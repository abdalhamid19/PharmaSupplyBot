"""Async live-order AI decision flow."""

from __future__ import annotations

from .matching.candidate_identity import candidate_has_store_product_id
from .drug_matching.ai.ai_provider_cooldown import apply_provider_cooldown
from .drug_matching.normalization.normalizer import components_match, parse_drug
from .matching_types import MatchDecision, SearchMatch
from .ordering.order_ai_matching import (
    OrderAiOutcome,
    accepted_search,
    ai_candidates,
    low_confidence,
    match_from_record,
    rejected_search,
)
from .utils.excel import Item


async def resolve_order_ai(settings, verifier, item, decision):
    """Return an OrderAiOutcome after verify/search/review."""
    verified, verify_result = await verify_current_match(
        settings, verifier, item, decision
    )
    if verified is not None:
        return verified
    searched = await _search(settings, verifier, item, decision, verify_result)
    return searched or OrderAiOutcome(
        decision,
        "ai_rejected",
        "No accepted AI match",
        0.0,
        True,
        verify_result=verify_result,
    )


async def _search(settings, verifier, item, decision, verify_result):
    result = await verifier.find_better_match(item.name, ai_candidates(decision))
    apply_provider_cooldown(verifier, result)
    if not result or not result.get("record"):
        return None
    
    confidence = float(result.get("confidence", 0.0) or 0.0)
    is_borderline = _is_borderline_search(result, confidence, settings)
    
    if confidence < settings.accept_confidence and not is_borderline:
        return low_confidence(decision, result, confidence, verify_result)
    
    return await _process_search_match(settings, verifier, item, decision, result, verify_result, confidence)


async def _process_search_match(settings, verifier, item, decision, result, verify_result, confidence):
    """Process the search match result."""
    match = match_from_record(result["record"], result.get("score", 0.0))
    local_rejection = local_match_rejection(item, match)
    if local_rejection:
        return rejected_search(decision, result, confidence, verify_result, local_rejection)
    
    reviewed = await review_order_ai(settings, verifier, item, match, confidence, result)
    if reviewed:
        return with_ai_results(reviewed, verify_result=verify_result, search_result=result)
    return accepted_search(decision, match, result, confidence, verify_result)


def _is_borderline_search(result, confidence, settings):
    """Check if search result is borderline accept requiring review."""
    is_correct = bool(result.get("is_correct"))
    is_accept = result.get("decision") == "accept"
    no_conflicts = not result.get("hard_conflicts")
    
    return (
        is_correct
        and is_accept
        and no_conflicts
        and settings.verify_soft_accept_confidence
        <= confidence
        < settings.accept_confidence
        and bool(settings.api_config.review_model)
    )


# Verification step
async def verify_current_match(settings, verifier, item, decision):
    """Return an AI outcome for the deterministic match, or None to search."""
    match = decision.best_match
    if not match:
        return None, {}
    if local_rejection := local_match_rejection(item, match):
        return None, local_rejection_result(local_rejection)
    
    result = await _verify_match(verifier, item, match, decision)
    apply_provider_cooldown(verifier, result)
    
    confidence = float(result.get("confidence", 0.0) or 0.0)
    is_borderline = _is_borderline_accept(result, confidence, settings)
    
    if not result.get("is_correct") or (confidence < settings.accept_confidence and not is_borderline):
        return None, result
    
    return await _finalize_verification(settings, verifier, item, match, confidence, result, decision)


async def _finalize_verification(settings, verifier, item, match, confidence, result, decision):
    """Finalize verification with review if needed."""
    reviewed = await review_order_ai(settings, verifier, item, match, confidence, result)
    if reviewed:
        return with_ai_results(reviewed, verify_result=result), result
    return _verified_outcome(decision, result, confidence), result


def _is_borderline_accept(result, confidence, settings):
    """Check if result is borderline accept requiring review."""
    is_correct = bool(result.get("is_correct"))
    is_accept = result.get("decision") == "accept"
    no_conflicts = not result.get("hard_conflicts")
    
    return (
        is_correct
        and is_accept
        and no_conflicts
        and settings.verify_soft_accept_confidence
        <= confidence
        < settings.accept_confidence
        and bool(settings.api_config.review_model)
    )


def _verified_outcome(decision, result, confidence):
    return OrderAiOutcome(
        decision,
        "ai_verified",
        str(result.get("reason", "")),
        confidence,
        verify_result=result,
    )


async def _verify_match(verifier, item, match, decision):
    return await verifier.verify_one(
        item.name,
        candidate_name(match.data),
        candidate_ar(match.data),
        match.score,
        decision.final_reason,
        candidate_price=candidate_price(match.data),
    )


# Review helpers
async def review_order_ai(settings, verifier, item, match, confidence, result):
    """Return a manual-review outcome when the review model rejects a match."""
    if not settings.api_config.review_model:
        return None
    review = await _review_match(verifier, item, match, confidence, result)
    apply_provider_cooldown(verifier, review)
    review_conf = float(review.get("confidence", confidence) or 0.0)
    if review.get("is_correct"):
        return None
    reason = str(review.get("reason", "review_rejected"))
    return OrderAiOutcome(
        MatchDecision(None, [], reason),
        "ai_review_rejected",
        reason,
        review_conf,
        True,
        review_result=review,
    )


def with_ai_results(outcome, **values):
    """Return an outcome copy with additional AI result dictionaries."""
    payload = {
        "verify_result": outcome.verify_result,
        "search_result": outcome.search_result,
        "review_result": outcome.review_result,
    }
    payload.update({key: value for key, value in values.items() if value})
    return OrderAiOutcome(
        outcome.decision,
        outcome.status,
        outcome.reason,
        outcome.confidence,
        outcome.manual_review,
        **payload,
    )


async def _review_match(verifier, item, match, confidence, result):
    return await verifier.review_one(
        item.name,
        candidate_name(match.data),
        "ai_found",
        confidence,
        str(result.get("reason", "")),
        drug_b_ar=candidate_ar(match.data),
    )


# Local safety checks
def local_match_rejection(item, match) -> str:
    """Return why an AI-selected match must not become orderable."""
    if not candidate_has_store_product_id(match.data):
        return "missing storeProductId"
    requested = parse_drug(item.name)
    offered = parse_drug(candidate_name(match.data))
    offered.is_synthetic = bool(match.data.get("productNameEnSynthetic"))
    if requested.brand and offered.brand:
        is_match, reason = components_match(requested, offered)
        if not is_match:
            return f"component mismatch: {reason}"
    return ""


def local_rejection_result(reason: str) -> dict[str, object]:
    """Return a verifier-shaped result for a local safety rejection."""
    return {
        "is_correct": False,
        "reason": f"local_safety: {reason}",
        "confidence": 0.0,
    }


# Candidate helpers (reused from matching)
def candidate_name(candidate: dict) -> str:
    """Return the English display name used in AI prompts."""
    return str(
        candidate.get("productNameEn")
        or candidate.get("productNameEnFallback")
        or candidate.get("productName")
        or ""
    )


def candidate_ar(candidate: dict) -> str:
    """Return the Arabic display name used in AI prompts."""
    return str(candidate.get("productName") or "")


def candidate_price(candidate: dict) -> object:
    """Return candidate price when Tawreed exposes one."""
    return (
        candidate.get("retailPrice") or candidate.get("publicPrice") or
        candidate.get("price") or candidate.get("sellingPrice")
    )


__all__ = [
    "resolve_order_ai",
    "verify_current_match",
    "review_order_ai",
    "with_ai_results",
    "local_match_rejection",
    "local_rejection_result",
]
