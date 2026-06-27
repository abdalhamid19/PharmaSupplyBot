"""AI search logic for finding matches among unmatched items."""

from __future__ import annotations

import asyncio
import logging
import re

import pandas as pd
from rapidfuzz import fuzz, process

from .config import MatchingConfig, APIConfig
from .normalizer import parse_drug, components_match
from .indexer import DrugIndex
from .pricing import price_context
from .verifier import AIVerifier

logger = logging.getLogger("pharmasupplybot.matching")

_AI_SEARCH_ACCEPT_CONFIDENCE = 0.75
_DANGEROUS_REVIEW_REASONS = frozenset((
    "different_age_group",
    "different_form",
    "different_route",
    "different_weight",
    "different_flavor",
    "different_product_class",
))


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


def _trace_skip_all_search(results, trace, reason):
    """Log AI search skip for all unmatched drugs."""
    unmatched = results[
        (results["matched_product_name_en"].isna()) |
        (results["matched_product_name_en"] == "")
    ]
    for idx, row in unmatched.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "search", reason, row_index=idx,
        )


async def run_ai_search(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI searches for matches among unmatched items."""
    if not api_cfg.api_key:
        logger.warning("No API key - skipping AI search")
        if trace and trace.enabled:
            _trace_skip_all_search(results, trace, "no_api_key")
        return results
    unmatched = _get_unmatched(results)
    if len(unmatched) == 0:
        logger.info("No unmatched items to search")
        return results
    original_unmatched = len(unmatched)
    if cfg.ai_search_limit is not None and len(unmatched) > cfg.ai_search_limit:
        skipped = unmatched.iloc[cfg.ai_search_limit:]
        unmatched = unmatched.iloc[:cfg.ai_search_limit]
        if trace and trace.enabled:
            for idx, row in skipped.iterrows():
                parsed = parse_drug(row["drug_name"])
                trace.log_ai_search_not_eligible(
                    row["code"], row["drug_name"],
                    parsed.normalized, parsed.brand,
                    f"ai_search_limit={cfg.ai_search_limit}",
                    row_index=idx,
                )
    logger.info(
        f"Phase 3: AI searching for matches "
        f"among {len(unmatched)} unmatched items"
        + (
            f" (limited from {original_unmatched})"
            if len(unmatched) != original_unmatched else ""
        ),
    )
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        found = await _search_batch(
            verifier, results, index, unmatched, cfg, trace,
        )
        logger.info(f"  AI Search found {found} new matches")
    return results


def _get_unmatched(results):
    return results[
        (results["matched_product_name_en"].isna()) |
        (results["matched_product_name_en"] == "")
    ].copy()


async def _search_batch(verifier, results, index, unmatched, cfg, trace):
    found = 0
    batch_size = cfg.ai_batch_size
    items = list(unmatched.iterrows())
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        raw_results = await asyncio.gather(*[
            _try_search_one(verifier, results, index, row, cfg, trace)
            for _, row in batch
        ], return_exceptions=True)
        batch_results = []
        for (_, row), item in zip(batch, raw_results):
            if isinstance(item, Exception):
                logger.warning(
                    "  ⚠ AI search exception for row=%s: %s",
                    row.name, item,
                )
                _trace_search_exception(trace, row, item)
                batch_results.append(0)
            else:
                batch_results.append(item)
        found += sum(batch_results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Searched {done}/{len(items)}, found {found}")
    return found


async def _try_search_one(verifier, results, index, row, cfg, trace):
    drug_name = row["drug_name"]
    parsed = parse_drug(drug_name)
    norm = parsed.normalized
    code = str(row.get("code", ""))
    if not norm or len(norm) < 3:
        if trace and trace.enabled:
            trace.log_ai_skip(
                code, drug_name, norm, parsed.brand,
                "search", "norm too short for AI search",
                row_index=row.name,
            )
        return 0
    price = row.get("_drug_price", "")
    candidates = _search_candidates(parsed, norm, index, cfg, price)
    if not candidates:
        if trace and trace.enabled:
            trace.log_ai_skip(
                code, drug_name, norm, parsed.brand,
                "search", "no valid candidates found",
                row_index=row.name,
            )
        return 0
    candidates = _eligible_search_candidates(parsed, candidates, index, cfg)
    if not candidates:
        if trace and trace.enabled:
            trace.log_ai_search_not_eligible(
                code, drug_name, norm, parsed.brand,
                (
                    "ai_search_skipped_not_eligible: "
                    f"no candidate >= {cfg.ai_search_min_candidate_score}"
                    " with safe components"
                ),
                row_index=row.name,
            )
        return 0
    if trace and trace.enabled:
        cand_names = [
            c[0]["product_name_en"] for c in candidates
        ]
        trace.log_ai_search_sent(
            code, drug_name, norm, parsed.brand,
            len(candidates), cand_names,
            ai_model=verifier._cfg.model,
            price_context=price_context(price, None),
            row_index=row.name,
        )
    ai_result = await verifier.find_better_match(
        drug_name, candidates, inventory_price=price,
    )
    if ai_result:
        _trace_api_attempts(trace, results, row.name, parsed, ai_result)
        _trace_parse_failure(trace, results, row.name, parsed, ai_result)
    confidence = ai_result.get("confidence", 0) if ai_result else 0
    accept_threshold, acceptance_reason = _search_acceptance_threshold(
        ai_result, candidates, parsed, index, cfg,
    )
    if (
        ai_result and ai_result.get("record")
        and confidence >= accept_threshold
        and acceptance_reason != "unsafe_component_mismatch"
    ):
        match_name = ai_result["record"]["product_name_en"]
        ai_result["_component_reason"] = acceptance_reason
        _apply_search_result(results, row.name, ai_result)
        if trace and trace.enabled:
            trace.log_ai_search_result(
                code, drug_name, norm, parsed.brand,
                True, match_name, confidence,
                model_used=ai_result.get("model_used", ""),
                api_failures=verifier.get_fallback_log(),
                accept_threshold=accept_threshold,
                row_index=row.name,
                parse_failed=ai_result.get("parse_failed", False),
            )
        return 1
    if trace and trace.enabled:
        error_code = _search_error_code(
            ai_result, confidence, accept_threshold,
        )
        if acceptance_reason == "unsafe_component_mismatch":
            error_code = acceptance_reason
        trace.log_ai_search_result(
            code, drug_name, norm, parsed.brand,
            False, None, confidence,
            model_used=ai_result.get("model_used", "") if ai_result else "",
            api_failures=verifier.get_fallback_log(),
            accept_threshold=accept_threshold,
            row_index=row.name,
            error_code=error_code,
            parse_failed=ai_result.get("parse_failed", False) if ai_result else False,
        )
    return 0


def _search_error_code(ai_result, confidence, accept_confidence) -> str:
    if not ai_result:
        return "no_ai_result"
    if ai_result.get("error_code"):
        return str(ai_result["error_code"])
    if ai_result.get("parse_failed"):
        return "invalid_json"
    if ai_result.get("best_index", 0) == 0:
        return "best_index_0"
    if confidence < accept_confidence:
        return "confidence_below_threshold"
    return "no_record"


def _trace_search_exception(trace, row, exc):
    if not trace or not trace.enabled:
        return
    drug_name = row["drug_name"]
    parsed = parse_drug(drug_name)
    trace.log_ai_search_result(
        str(row.get("code", "")), drug_name, parsed.normalized, parsed.brand,
        False, None, 0,
        api_failures=f"{type(exc).__name__}: {str(exc)[:180]}",
        accept_threshold=_AI_SEARCH_ACCEPT_CONFIDENCE,
        row_index=row.name,
        error_code="ai_search_exception",
    )


def _search_candidates(parsed, norm, index, cfg, price=None):
    """Gather fuzzy + brand candidates for unmatched search."""
    candidates = []
    limit = cfg.ai_search_candidate_limit
    for idx, score in index.get_candidates(parsed, limit=limit, price=price):
        _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    for scorer in [fuzz.token_set_ratio, fuzz.token_sort_ratio]:
        results = process.extract(
            norm, index.norms,
            scorer=scorer, limit=limit,
        )
        for _, score, idx in results:
            if score >= cfg.ai_search_review_candidate_min_score:
                _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    brand_hits = index.lookup_by_brand(parsed)
    for rec, idx in brand_hits:
        score = index.score_candidate(norm, idx)
        if score >= cfg.ai_search_review_candidate_min_score:
            _append_search_candidate(candidates, parsed, index, cfg, idx, score)
    return _dedupe_candidates(candidates)


def _eligible_search_candidates(parsed, candidates, index, cfg):
    eligible = []
    review_count = 0
    for candidate in candidates:
        rec, score, idx = candidate[:3]
        ok, reason = _candidate_component_status(candidate, parsed, index, cfg)
        if ok and score >= cfg.ai_search_min_candidate_score:
            eligible.append(candidate)
        elif (
            not ok
            and
            _review_candidates_enabled(cfg)
            and score >= cfg.ai_search_review_candidate_min_score
            and review_count < cfg.ai_search_review_candidate_limit
            and _is_reviewable_component_mismatch(parsed, index.get_parsed(idx), reason, score, cfg)
        ):
            eligible.append(_with_candidate_reason(candidate, reason))
            review_count += 1
    return eligible


def _dedupe_candidates(candidates):
    seen = set()
    out = []
    for candidate in candidates:
        rec = candidate[0]
        sid = rec["store_product_id"]
        if sid not in seen:
            seen.add(sid)
            out.append(candidate)
    return out


def _append_search_candidate(candidates, parsed, index, cfg, idx, score):
    candidate = index.get_parsed(idx)
    ok, reason = components_match(
        parsed, candidate,
        cfg.brand_prefix_min,
    )
    if ok or _is_reviewable_component_mismatch(parsed, candidate, reason, score, cfg):
        candidates.append((index.get_record(idx), score, idx, reason))


def _candidate_component_status(candidate, parsed, index, cfg):
    reason = candidate[3] if len(candidate) > 3 else ""
    if reason:
        return reason == "ok", reason
    return components_match(
        parsed, index.get_parsed(candidate[2]),
        cfg.brand_prefix_min,
    )


def _with_candidate_reason(candidate, reason):
    if len(candidate) > 3:
        return candidate
    return (*candidate, reason)


def _review_candidates_enabled(cfg) -> bool:
    return cfg.ai_search_policy in {
        "review-candidates", "expanded", "aggressive",
    }


def _is_reviewable_component_mismatch(parsed, candidate, reason, score, cfg) -> bool:
    if reason == "ok":
        return True
    if reason in _DANGEROUS_REVIEW_REASONS:
        return False
    if reason not in cfg.ai_search_allow_component_mismatch_reasons:
        return False
    if reason == "different_brand":
        return _brand_similarity(parsed.brand, candidate.brand) >= 80
    if reason in {"different_quantity", "different_volume"}:
        return _brand_similarity(parsed.brand, candidate.brand) >= 86
    if reason == "different_modifier" and parsed.product_class == "medicine":
        return score >= max(cfg.ai_search_review_candidate_min_score, 75)
    return True


def _brand_similarity(left: str, right: str) -> float:
    left_clean = re.sub(r"[^A-Z0-9]", "", left)
    right_clean = re.sub(r"[^A-Z0-9]", "", right)
    if not left_clean or not right_clean:
        return 0.0
    if left_clean in right_clean or right_clean in left_clean:
        return 100.0
    return fuzz.ratio(left_clean, right_clean)


def _search_acceptance_threshold(ai_result, candidates, parsed, index, cfg):
    threshold = cfg.ai_search_accept_confidence
    if not ai_result or not ai_result.get("record"):
        return threshold, "no_record"
    best_index = ai_result.get("best_index", 0)
    if not isinstance(best_index, int) or best_index <= 0 or best_index > len(candidates):
        return threshold, "invalid_best_index"
    candidate = candidates[best_index - 1]
    ok, reason = _candidate_component_status(candidate, parsed, index, cfg)
    if ok:
        return threshold, "ok"
    if not _is_reviewable_component_mismatch(
        parsed, index.get_parsed(candidate[2]), reason, candidate[1], cfg,
    ):
        return max(threshold, cfg.ai_search_review_accept_confidence), "unsafe_component_mismatch"
    return max(threshold, cfg.ai_search_review_accept_confidence), reason


def _apply_search_result(results, idx, ai_result):
    rec = ai_result["record"]
    results.at[idx, "matched_product_name_en"] = rec["product_name_en"]
    results.at[idx, "matched_product_name_ar"] = rec["product_name_ar"]
    results.at[idx, "matched_store_product_id"] = rec["store_product_id"]
    results.at[idx, "match_score"] = round(ai_result.get("score", 0), 1)
    results.at[idx, "verified"] = "ai_found"
    results.at[idx, "match_method"] = "ai_search"
    results.at[idx, "ai_confidence"] = round(ai_result.get("confidence", 0), 2)
    component_reason = ai_result.get("_component_reason", "")
    if component_reason and component_reason != "ok":
        results.at[idx, "_ai_component_reason"] = component_reason
    _set_internal_matched_price(results, idx, rec.get("price", ""))
