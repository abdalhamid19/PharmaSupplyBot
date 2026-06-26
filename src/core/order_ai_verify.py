"""Verification step for live-order AI matching."""

from __future__ import annotations

from .drug_matching.ai_provider_cooldown import apply_provider_cooldown
from .order_ai_records import candidate_ar, candidate_name, candidate_price
from .order_ai_review import review_order_ai, with_ai_results
from .order_ai_safety import local_match_rejection, local_rejection_result


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
    from .order_ai_matching import OrderAiOutcome

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
