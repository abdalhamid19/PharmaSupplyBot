"""AI verification logic for drug matching."""

from __future__ import annotations

import logging
import pandas as pd

from .config import MatchingConfig, APIConfig
from .normalizer import parse_drug, components_match
from .indexer import DrugIndex
from .pricing import price_context
from .verifier import AIVerifier

logger = logging.getLogger("pharmasupplybot.matching")

_FUZZY_VERIFY_METHODS = frozenset((
    "token_set_ratio",
    "token_sort_ratio",
    "partial_token_sort_ratio",
))


# Export helper functions for use by ai_review.py
__all__ = [
    "run_ai_verification",
    "_internal_value",
    "_set_internal_matched_price",
    "_trace_api_attempts",
    "_trace_parse_failure",
    "_clear_match",
    "_apply_correction",
]


def _internal_value(results: pd.DataFrame, idx, col: str, default=""):
    return results.at[idx, col] if col in results.columns else default


def _set_internal_matched_price(results: pd.DataFrame, idx, value):
    if "_matched_price" in results.columns:
        results["_matched_price"] = results["_matched_price"].astype(object)
    results.at[idx, "_matched_price"] = value


def _trace_api_attempts(trace, results, idx, parsed, item):
    if trace and trace.enabled:
        trace.log_api_attempts(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("_api_attempts", []), row_index=idx,
        )


def _trace_parse_failure(trace, results, idx, parsed, item):
    if trace and trace.enabled and item.get("parse_failed"):
        trace.log_ai_parse_failure(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            item.get("reason", ""),
            model_used=item.get("model_used", ""),
            row_index=idx,
        )


def _trace_skip_all_verify(results, trace, reason):
    """Log AI verify skip for all eligible drugs."""
    matched = results[results["matched_product_name_en"] != ""]
    scores = pd.to_numeric(matched["match_score"], errors="coerce")
    eligible = matched[scores < 90]
    for idx, row in eligible.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "verify", reason, row_index=idx,
        )


async def run_ai_verification(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI verification of matches below threshold."""
    if not api_cfg.api_key:
        logger.warning("No API key - skipping AI verification")
        if trace and trace.enabled:
            _trace_skip_all_verify(results, trace, "no_api_key")
        return results
    to_verify = _select_for_verification(results, cfg)
    if len(to_verify) == 0:
        logger.info("No matches below AI verification threshold")
        return results
    logger.info(
        f"Phase 2: Verifying {len(to_verify)} matches "
        f"with AI (threshold={cfg.ai_verify_threshold})",
    )
    if trace and trace.enabled:
        for idx, row in to_verify.iterrows():
            parsed = parse_drug(row["drug_name"])
            score = pd.to_numeric(row["match_score"], errors="coerce")
            trace.log_ai_verify_sent(
                row["code"], row["drug_name"],
                parsed.normalized, parsed.brand,
                score, cfg.ai_verify_threshold,
                row["matched_product_name_en"],
                parsed.brand, row["match_method"],
                ai_model=api_cfg.model,
                price_context=price_context(
                    row.get("_drug_price", ""),
                    row.get("_matched_price", ""),
                ),
                row_index=idx,
            )
    items = _build_verify_items(to_verify)
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        all_results = await _batch_verify(verifier, items, cfg)
        rejected, corrected = await _apply_verification(
            verifier, results, index, all_results, cfg, trace,
        )
        logger.info(
            f"  AI Results: "
            f"confirmed={len(all_results)-rejected-corrected}, "
            f"corrected={corrected}, rejected={rejected}",
        )
    return results


def _select_for_verification(results, cfg):
    matched = results[results["matched_product_name_en"] != ""].copy()
    scores = pd.to_numeric(matched["match_score"], errors="coerce")
    policy = getattr(cfg, "ai_verify_policy", "score")
    methods = matched["match_method"].fillna("")
    if policy == "all":
        selected = matched
    elif policy == "all-non-exact":
        selected = matched[
            ~((methods == "component_index") & (scores >= 100.0))
        ]
    elif policy == "fuzzy":
        selected = matched[
            (scores < cfg.ai_verify_threshold) |
            methods.isin(_FUZZY_VERIFY_METHODS)
        ]
    else:
        selected = matched[scores < cfg.ai_verify_threshold]
    if cfg.ai_verify_limit is not None:
        selected = selected.head(cfg.ai_verify_limit)
    return selected


def _build_verify_items(to_verify):
    return [
        (
            row["drug_name"],
            row["matched_product_name_en"],
            row.get("matched_product_name_ar", ""),
            idx,
            row.get("match_score", ""),
            row.get("match_method", ""),
            row.get("_drug_price", ""),
            row.get("_matched_price", ""),
        )
        for idx, row in to_verify.iterrows()
    ]


async def _batch_verify(verifier, items, cfg):
    all_results = []
    batch_size = cfg.ai_batch_size
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await verifier.verify_batch(batch)
        all_results.extend(results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Verified {done}/{len(items)}")
    return all_results


async def _apply_verification(
    verifier, results, index, all_results, cfg, trace,
):
    rejected = 0
    corrected = 0
    for vr in all_results:
        idx = vr.get("row_idx")
        if idx is None:
            continue
        drug_name = results.at[idx, "drug_name"]
        parsed = parse_drug(drug_name)
        _trace_api_attempts(trace, results, idx, parsed, vr)
        if not vr["is_correct"]:
            c, r = await _handle_rejected(
                verifier, results, index, idx, cfg, trace, vr,
            )
            corrected += c
            rejected += r
        else:
            results.at[idx, "verified"] = "ai_confirmed"
            results.at[idx, "match_method"] = "ai_verified"
            results.at[idx, "ai_confidence"] = round(vr.get("confidence", 0), 2)
            if trace and trace.enabled:
                ai_reason = vr.get("reason", "")
                if vr.get("api_failed"):
                    ai_reason = f"API unavailable ({ai_reason}), kept algo match"
                trace.log_ai_verify_result(
                    results.at[idx, "code"], drug_name,
                    parsed.normalized, parsed.brand,
                    True, "ai_confirmed",
                    "AI confirmed the algorithmic match",
                    results.at[idx, "matched_product_name_en"],
                    vr.get("confidence"), ai_reason,
                    "",
                    model_used=vr.get("model_used", ""),
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=vr.get("parse_failed", False),
                )
                _trace_parse_failure(trace, results, idx, parsed, vr)
    return rejected, corrected


async def _handle_rejected(verifier, results, index, idx, cfg, trace, vr):
    drug_name = results.at[idx, "drug_name"]
    parsed = parse_drug(drug_name)
    norm = parsed.normalized
    candidates = index.fuzzy_match(norm, top_k=5)
    valid = [
        (rec, score, cidx) for rec, score, cidx in candidates
        if components_match(
            parsed, index.get_parsed(cidx),
            cfg.brand_prefix_min,
        )[0]
    ]
    if valid:
        ai_result = await verifier.find_better_match(
            drug_name, valid,
            inventory_price=_internal_value(results, idx, "_drug_price"),
        )
        if ai_result and ai_result.get("record"):
            _apply_correction(results, idx, ai_result)
            if trace and trace.enabled:
                rec = ai_result["record"]
                trace.log_ai_verify_result(
                    results.at[idx, "code"], drug_name,
                    norm, parsed.brand,
                    False, "ai_corrected",
                    f"AI rejected original, found better: "
                    f"{rec['product_name_en']}",
                    results.at[idx, "matched_product_name_en"],
                    ai_result.get("confidence"),
                    ai_result.get("reason", ""),
                    rec["product_name_en"],
                    model_used=ai_result.get("model_used", ""),
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=ai_result.get("parse_failed", False),
                )
                _trace_api_attempts(trace, results, idx, parsed, ai_result)
                _trace_parse_failure(trace, results, idx, parsed, ai_result)
            return 1, 0
    _clear_match(results, idx)
    results.at[idx, "verified"] = "ai_rejected"
    results.at[idx, "match_method"] = "ai_verified"
    results.at[idx, "ai_confidence"] = round(vr.get("confidence", 0), 2)
    if trace and trace.enabled:
        trace.log_ai_verify_result(
            results.at[idx, "code"], drug_name,
            norm, parsed.brand,
            False, "ai_rejected",
            "AI rejected and no better match found",
            results.at[idx, "matched_product_name_en"],
            vr.get("confidence"), vr.get("reason", ""),
            "",
            model_used=vr.get("model_used", ""),
            api_failures=verifier.get_fallback_log(),
            row_index=idx,
            parse_failed=vr.get("parse_failed", False),
        )
        _trace_parse_failure(trace, results, idx, parsed, vr)
    return 0, 1


def _apply_correction(results, idx, ai_result):
    rec = ai_result["record"]
    results.at[idx, "matched_product_name_en"] = rec["product_name_en"]
    results.at[idx, "matched_product_name_ar"] = rec["product_name_ar"]
    results.at[idx, "matched_store_product_id"] = rec["store_product_id"]
    results.at[idx, "match_score"] = round(ai_result["score"], 1)
    results.at[idx, "verified"] = "ai_corrected"
    results.at[idx, "match_method"] = "ai_verified"
    results.at[idx, "ai_confidence"] = round(ai_result.get("confidence", 0), 2)
    _set_internal_matched_price(results, idx, rec.get("price", ""))


def _clear_match(results, idx):
    for col in (
        "matched_product_name_en", "matched_product_name_ar",
        "matched_store_product_id", "match_score", "_matched_price",
    ):
        if col not in results.columns:
            continue
        results[col] = results[col].astype(object)
        results.at[idx, col] = ""
