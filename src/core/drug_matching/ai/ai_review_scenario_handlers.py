"""Scenario handlers for AI review - handles different review result scenarios."""

from ..config import MatchingConfig
from ..indexing.indexer import DrugIndex
from ..normalization.normalizer import parse_drug, components_match
from ..verification.verifier import AIVerifier
from .ai_verify import (
    _trace_api_attempts, _trace_parse_failure, _clear_match,
    _apply_correction, _internal_value
)

_AI_REVIEW_OVERRIDE_CONFIDENCE = 0.75


def handle_api_failed(
    verifier, results, trace, idx, drug_name, parsed, is_correct,
    review_confidence, review_reason, rr,
):
    """Handle items where first AI had API failure."""
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
        return 0
    else:
        # Second model says this is NOT a correct match
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
        return 1


def handle_agreement(
    verifier, results, trace, idx, drug_name, parsed, first_decision,
    review_confidence, review_reason, rr,
):
    """Handle items where second model agrees with first AI."""
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


async def handle_disagreement(
    verifier, results, index, cfg, trace, idx, drug_name, parsed,
    first_decision, review_confidence, review_reason, rr,
):
    """Handle items where second model disagrees with first AI."""
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
        return 0
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
    return 1
