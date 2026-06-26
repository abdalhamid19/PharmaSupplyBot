"""Async live-order AI decision flow."""

from __future__ import annotations

from .drug_matching.ai_provider_cooldown import apply_provider_cooldown
from .order_ai_outcomes import accepted_search, low_confidence, rejected_search
from .order_ai_records import ai_candidates, match_from_record
from .order_ai_review import review_order_ai, with_ai_results
from .order_ai_safety import local_match_rejection
from .order_ai_verify import verify_current_match


async def resolve_order_ai(settings, verifier, item, decision):
    """Return an OrderAiOutcome after verify/search/review."""
    from .order_ai_matching import OrderAiOutcome

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
