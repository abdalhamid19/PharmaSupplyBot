"""Async live-order AI decision flow."""
from __future__ import annotations

from .order_ai_outcomes import accepted_search, low_confidence, rejected_search
from .order_ai_records import (
    ai_candidates,
    candidate_ar,
    candidate_name,
    candidate_price,
    match_from_record,
)
from .order_ai_review import review_order_ai, with_ai_results
from .order_ai_safety import local_match_rejection, local_rejection_result
async def resolve_order_ai(settings, verifier, item, decision):
    """Return an OrderAiOutcome after verify/search/review."""
    from .order_ai_matching import OrderAiOutcome

    verified, verify_result = await _verify_current(settings, verifier, item, decision)
    if verified is not None:
        return verified
    searched = await _search(settings, verifier, item, decision, verify_result)
    return searched or OrderAiOutcome(
        decision, "ai_rejected", "No accepted AI match", 0.0, True,
        verify_result=verify_result,
    )
async def _verify_current(settings, verifier, item, decision):
    from .order_ai_matching import OrderAiOutcome

    match = decision.best_match
    if not match:
        return None, {}
    local_rejection = local_match_rejection(item, match)
    if local_rejection:
        return None, local_rejection_result(local_rejection)
    result = await _verify_match(verifier, item, match, decision)
    confidence = float(result.get("confidence", 0.0) or 0.0)
    if not result.get("is_correct") or confidence < settings.accept_confidence:
        return None, result
    reviewed = await review_order_ai(settings, verifier, item, match, confidence, result)
    if reviewed:
        return with_ai_results(reviewed, verify_result=result), result
    return OrderAiOutcome(
        decision, "ai_verified", str(result.get("reason", "")), confidence,
        verify_result=result,
    ), result


async def _verify_match(verifier, item, match, decision):
    return await verifier.verify_one(
        item.name,
        candidate_name(match.data),
        candidate_ar(match.data),
        match.score,
        decision.final_reason,
        candidate_price=candidate_price(match.data),
    )


async def _search(settings, verifier, item, decision, verify_result):
    result = await verifier.find_better_match(item.name, ai_candidates(decision))
    if not result or not result.get("record"):
        return None
    confidence = float(result.get("confidence", 0.0) or 0.0)
    if confidence < settings.accept_confidence:
        return low_confidence(decision, result, confidence, verify_result)
    match = match_from_record(result["record"], result.get("score", 0.0))
    local_rejection = local_match_rejection(item, match)
    if local_rejection:
        return rejected_search(
            decision, result, confidence, verify_result, local_rejection
        )
    reviewed = await review_order_ai(settings, verifier, item, match, confidence, result)
    if reviewed:
        return with_ai_results(
            reviewed, verify_result=verify_result, search_result=result
        )
    return accepted_search(decision, match, result, confidence, verify_result)
