"""AI verification and search steps extracted from pipeline."""
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
_AI_REVIEW_OVERRIDE_CONFIDENCE = 0.75
_DANGEROUS_REVIEW_REASONS = frozenset((
    "different_age_group",
    "different_form",
    "different_route",
    "different_weight",
    "different_flavor",
    "different_product_class",
))
_FUZZY_VERIFY_METHODS = frozenset((
    "token_set_ratio",
    "token_sort_ratio",
    "partial_token_sort_ratio",
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


async def run_ai_review(
    results: pd.DataFrame,
    index: DrugIndex,
    cfg: MatchingConfig,
    api_cfg: APIConfig,
    trace=None,
) -> pd.DataFrame:
    """AI review: second model cross-verifies low-confidence AI decisions."""
    if not api_cfg.api_key or not api_cfg.review_model:
        logger.info("No review model configured - skipping AI review")
        if trace and trace.enabled:
            _trace_skip_all_review(results, trace, "no_review_model")
        return results
    if api_cfg.review_model == "rotation" and not api_cfg.review_attempt_plan:
        logger.info("No strong review model available - skipping AI review")
        if trace and trace.enabled:
            _trace_skip_all_review(results, trace, "no_strong_review_model")
        return results
    to_review = _select_for_review(results, cfg)
    if len(to_review) == 0:
        logger.info("No low-confidence AI decisions to review")
        return results
    logger.info(
        f"Phase 4: Reviewing {len(to_review)} low-confidence AI decisions "
        f"with second model (threshold={cfg.ai_review_threshold})",
    )
    if trace and trace.enabled:
        for idx, row in to_review.iterrows():
            parsed = parse_drug(row["drug_name"])
            conf = pd.to_numeric(row.get("ai_confidence", 0), errors="coerce")
            is_api_failed = (conf == 0.0)
            trace.log_ai_review_sent(
                row["code"], row["drug_name"],
                parsed.normalized, parsed.brand,
                row["verified"], row["ai_confidence"],
                row["matched_product_name_en"],
                first_model=api_cfg.model,
                review_model=api_cfg.review_model,
                api_failed=is_api_failed,
                price_context=price_context(
                    row.get("_drug_price", ""),
                    row.get("_matched_price", ""),
                ),
                row_index=idx,
            )
    items = _build_review_items(to_review)
    async with AIVerifier(
        api_cfg, max_concurrent=cfg.ai_max_concurrent,
    ) as verifier:
        all_results = await _batch_review(verifier, items, cfg)
        overridden = await _apply_review_results(
            verifier, results, index, all_results, cfg, trace,
        )
        logger.info(
            f"  Review Results: "
            f"confirmed={len(all_results)-overridden}, "
            f"overridden={overridden}",
        )
    return results


# --- helpers ---


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


# --- helpers ---

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


def _component_review_required(results, idx) -> str:
    if "_ai_component_reason" not in results.columns:
        return ""
    reason = results.at[idx, "_ai_component_reason"]
    if reason is None or pd.isna(reason):
        return ""
    reason = str(reason)
    return "" if reason.lower() == "nan" else reason


def _safe_reviewed_component_mismatch(results, idx, cfg, reason: str) -> bool:
    if reason not in {"different_brand", "brand_prefix_mismatch"}:
        return False
    parsed = parse_drug(results.at[idx, "drug_name"])
    matched = parse_drug(results.at[idx, "matched_product_name_en"])
    if _brand_similarity(parsed.brand, matched.brand) < 84:
        return False
    unsafe_checks = (
        parsed.dosage_nums and matched.dosage_nums
        and parsed.dosage_nums != matched.dosage_nums,
        parsed.form and matched.form and parsed.form != matched.form,
        parsed.qty and matched.qty and parsed.qty != matched.qty,
        parsed.volume and matched.volume and parsed.volume != matched.volume,
    )
    if any(unsafe_checks):
        return False
    return True


def _reject_reviewed_component_mismatch(
    verifier, results, idx, parsed, review_confidence, review_reason, trace, rr,
):
    _clear_match(results, idx)
    results.at[idx, "verified"] = "ai_review_rejected"
    results.at[idx, "match_method"] = "ai_reviewed"
    results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
    if trace and trace.enabled:
        trace.log_ai_review_result(
            results.at[idx, "code"], results.at[idx, "drug_name"],
            parsed.normalized, parsed.brand,
            False, review_confidence, review_reason,
            "ai_review_rejected",
            review_model=verifier._cfg.review_model,
            api_failures=verifier.get_fallback_log(),
            row_index=idx,
            parse_failed=rr.get("parse_failed", False),
        )


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


# --- review helpers ---


def _select_for_review(results, cfg):
    """Select AI-verified results for review.
    - Genuine low-confidence decisions (confidence > 0 but < threshold): normal review
    - API-failed decisions (confidence == 0): sent for fresh verification (no first-AI opinion)"""
    ai_verified = results[
        results["verified"].isin(["ai_confirmed", "ai_corrected", "ai_found", "ai_rejected"])
    ].copy()
    if len(ai_verified) == 0:
        return ai_verified
    confidences = pd.to_numeric(ai_verified["ai_confidence"], errors="coerce")
    component_reasons = (
        ai_verified["_ai_component_reason"].fillna("").astype(str)
        if "_ai_component_reason" in ai_verified.columns
        else pd.Series("", index=ai_verified.index)
    )
    component_reasons = component_reasons.replace("nan", "")
    component_review = ai_verified[component_reasons != ""]
    # API-failed items (confidence == 0) need fresh verification
    api_failed = ai_verified[confidences == 0.0]
    # Genuine low-confidence items need normal review
    genuine = ai_verified[confidences > 0.0]
    if len(genuine) > 0:
        genuine_confidences = pd.to_numeric(genuine["ai_confidence"], errors="coerce")
        genuine = genuine[genuine_confidences < cfg.ai_review_threshold]
    # Combine both groups
    return pd.concat([api_failed, genuine, component_review]).drop_duplicates()


def _build_review_items(to_review):
    """Build review items: (drug_a, drug_b, first_decision, first_confidence, first_reason, row_idx, api_failed)."""
    items = []
    for idx, row in to_review.iterrows():
        drug_a = row["drug_name"]
        drug_b = row.get("matched_product_name_en", "")
        drug_b_ar = row.get("matched_product_name_ar", "")
        first_decision = row.get("verified", "")
        first_confidence = pd.to_numeric(row.get("ai_confidence", 0), errors="coerce")
        if pd.isna(first_confidence):
            first_confidence = 0.0
        # Mark items where first AI had API failure (confidence=0 from fallback)
        is_api_failed = first_confidence == 0.0
        component_reason = str(row.get("_ai_component_reason", ""))
        first_reason = "API unavailable - no first AI decision was made" if is_api_failed else component_reason
        items.append((
            drug_a, drug_b or "", drug_b_ar or "", first_decision,
            first_confidence, first_reason, idx, is_api_failed,
            row.get("_drug_price", ""), row.get("_matched_price", ""),
        ))
    return items


async def _batch_review(verifier, items, cfg):
    """Review a batch of items with the second model."""
    all_results = []
    batch_size = cfg.ai_batch_size
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await verifier.review_batch(batch)
        # Propagate api_failed flag from items to results
        for j, r in enumerate(results):
            r["api_failed"] = batch[j][7]
        all_results.extend(results)
        done = min(i + batch_size, len(items))
        logger.info(f"  Reviewed {done}/{len(items)}")
    return all_results


async def _apply_review_results(
    verifier, results, index, all_results, cfg, trace,
):
    """Apply review results: if second model disagrees, re-evaluate.
    For api_failed items, is_correct is a direct fresh decision."""
    overridden = 0
    for rr in all_results:
        idx = rr.get("row_idx")
        if idx is None:
            continue
        drug_name = results.at[idx, "drug_name"]
        parsed = parse_drug(drug_name)
        first_decision = results.at[idx, "verified"]
        review_confidence = rr.get("confidence", 0)
        review_confidence = pd.to_numeric(review_confidence, errors="coerce")
        if pd.isna(review_confidence):
            review_confidence = 0.0
        review_reason = rr.get("reason", "")
        is_correct = rr.get("is_correct", True)
        is_api_failed = rr.get("api_failed", False)
        component_reason = _component_review_required(results, idx)
        _trace_api_attempts(trace, results, idx, parsed, rr)
        _trace_parse_failure(trace, results, idx, parsed, rr)

        if is_api_failed:
            # First AI never made a real decision — second model's result is the primary decision
            if is_correct and review_confidence >= _AI_REVIEW_OVERRIDE_CONFIDENCE:
                results.at[idx, "verified"] = "ai_confirmed"
                results.at[idx, "match_method"] = "ai_verified"
                results.at[idx, "ai_confidence"] = round(review_confidence, 2)
                results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
                if trace and trace.enabled:
                    trace.log_ai_review_result(
                        results.at[idx, "code"], drug_name,
                        parsed.normalized, parsed.brand,
                        True, review_confidence, review_reason,
                        "ai_confirmed (fresh verify by review model)",
                        review_model=verifier._cfg.review_model,
                        api_failures=verifier.get_fallback_log(),
                        row_index=idx,
                        parse_failed=rr.get("parse_failed", False),
                    )
            else:
                # Second model says this is NOT a correct match
                overridden += 1
                _clear_match(results, idx)
                results.at[idx, "verified"] = "ai_review_rejected"
                results.at[idx, "match_method"] = "ai_reviewed"
                results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
                if trace and trace.enabled:
                    trace.log_ai_review_result(
                        results.at[idx, "code"], drug_name,
                        parsed.normalized, parsed.brand,
                        False, review_confidence, review_reason,
                        "ai_review_rejected (fresh verify by review model)",
                        review_model=verifier._cfg.review_model,
                        api_failures=verifier.get_fallback_log(),
                        row_index=idx,
                        parse_failed=rr.get("parse_failed", False),
                    )
        elif (
            component_reason
            and first_decision in {"ai_confirmed", "ai_corrected", "ai_found"}
            and (
                not is_correct
                or review_confidence < max(
                    _AI_REVIEW_OVERRIDE_CONFIDENCE,
                    cfg.ai_search_review_accept_confidence,
                )
                or not _safe_reviewed_component_mismatch(
                    results, idx, cfg, component_reason,
                )
            )
        ):
            overridden += 1
            _reject_reviewed_component_mismatch(
                verifier, results, idx, parsed, review_confidence,
                review_reason or f"component mismatch: {component_reason}",
                trace, rr,
            )
        elif is_correct:
            # Second model agrees with first AI
            results.at[idx, "verified"] = f"{first_decision}_reviewed"
            results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
            if trace and trace.enabled:
                trace.log_ai_review_result(
                    results.at[idx, "code"], drug_name,
                    parsed.normalized, parsed.brand,
                    True, review_confidence, review_reason,
                    f"{first_decision}_reviewed",
                    review_model=verifier._cfg.review_model,
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=rr.get("parse_failed", False),
                )
        else:
            # Second model disagrees with first AI
            if review_confidence < _AI_REVIEW_OVERRIDE_CONFIDENCE:
                results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
                if trace and trace.enabled:
                    trace.log_ai_review_result(
                        results.at[idx, "code"], drug_name,
                        parsed.normalized, parsed.brand,
                        True, review_confidence, review_reason,
                        f"{first_decision}_kept_low_confidence_review",
                        review_model=verifier._cfg.review_model,
                        api_failures=verifier.get_fallback_log(),
                        row_index=idx,
                        parse_failed=rr.get("parse_failed", False),
                    )
                continue
            overridden += 1
            if first_decision in ("ai_confirmed", "ai_corrected", "ai_found"):
                # First AI said correct, second says wrong -> reject
                _clear_match(results, idx)
                results.at[idx, "verified"] = "ai_review_rejected"
                results.at[idx, "match_method"] = "ai_reviewed"
                results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
            elif first_decision == "ai_rejected":
                # First AI rejected, second says correct -> try to find match
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
                        inventory_price=_internal_value(
                            results, idx, "_drug_price",
                        ),
                    )
                    if ai_result:
                        _trace_api_attempts(trace, results, idx, parsed, ai_result)
                        _trace_parse_failure(trace, results, idx, parsed, ai_result)
                    if ai_result and ai_result.get("record"):
                        _apply_correction(results, idx, ai_result)
                        results.at[idx, "verified"] = "ai_review_corrected"
                        results.at[idx, "match_method"] = "ai_reviewed"
                        results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
                    else:
                        results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
                else:
                    results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
            else:
                results.at[idx, "ai_review_confidence"] = round(review_confidence, 2)
            if trace and trace.enabled:
                trace.log_ai_review_result(
                    results.at[idx, "code"], drug_name,
                    parsed.normalized, parsed.brand,
                    False, review_confidence, review_reason,
                    results.at[idx, "verified"],
                    review_model=verifier._cfg.review_model,
                    api_failures=verifier.get_fallback_log(),
                    row_index=idx,
                    parse_failed=rr.get("parse_failed", False),
                )
    return overridden


def _trace_skip_all_review(results, trace, reason):
    """Log AI review skip for all AI-verified drugs."""
    ai_verified = results[
        results["verified"].isin(["ai_confirmed", "ai_corrected", "ai_found", "ai_rejected"])
    ]
    for idx, row in ai_verified.iterrows():
        parsed = parse_drug(row["drug_name"])
        trace.log_ai_skip(
            row["code"], row["drug_name"],
            parsed.normalized, parsed.brand,
            "review", reason, row_index=idx,
        )
