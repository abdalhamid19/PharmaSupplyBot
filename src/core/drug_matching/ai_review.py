"""AI review logic for cross-verifying low-confidence AI decisions."""

from __future__ import annotations

import logging
import re

import pandas as pd
from rapidfuzz import fuzz

from .config import MatchingConfig, APIConfig
from .normalizer import parse_drug, components_match
from .indexer import DrugIndex
from .pricing import price_context
from .verifier import AIVerifier
from .ai_verify import (
    _internal_value, _set_internal_matched_price, _trace_api_attempts,
    _trace_parse_failure, _clear_match, _apply_correction
)

logger = logging.getLogger("pharmasupplybot.matching")

_AI_REVIEW_OVERRIDE_CONFIDENCE = 0.75


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
                verifier, results, idx, parsed, review_confidence, review_reason, trace, rr,
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


def _brand_similarity(left: str, right: str) -> float:
    left_clean = re.sub(r"[^A-Z0-9]", "", left)
    right_clean = re.sub(r"[^A-Z0-9]", "", right)
    if not left_clean or not right_clean:
        return 0.0
    if left_clean in right_clean or right_clean in left_clean:
        return 100.0
    return fuzz.ratio(left_clean, right_clean)
