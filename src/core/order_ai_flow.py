"""Async live-order AI decision flow."""
from __future__ import annotations

from .matching_models import MatchDecision
from .order_ai_records import (
    ai_candidates,
    candidate_ar,
    candidate_name,
    candidate_price,
    match_from_record,
)
async def resolve_order_ai(settings, verifier, item, decision):
    """Return an OrderAiOutcome after verify/search/review."""
    from .order_ai_matching import OrderAiOutcome

    verified = await _verify_current(settings, verifier, item, decision)
    if verified is not None:
        return verified
    searched = await _search(settings, verifier, item, decision)
    return searched or OrderAiOutcome(
        decision, "ai_rejected", "No accepted AI match", 0.0, True
    )
async def _verify_current(settings, verifier, item, decision):
    from .order_ai_matching import OrderAiOutcome

    match = decision.best_match
    if not match:
        return None
    result = await _verify_match(verifier, item, match, decision)
    confidence = float(result.get("confidence", 0.0) or 0.0)
    if not result.get("is_correct") or confidence < settings.accept_confidence:
        return None
    reviewed = await _review(settings, verifier, item, match, confidence, result)
    if reviewed:
        return reviewed
    return OrderAiOutcome(decision, "ai_verified", str(result.get("reason", "")), confidence)


async def _verify_match(verifier, item, match, decision):
    return await verifier.verify_one(
        item.name,
        candidate_name(match.data),
        candidate_ar(match.data),
        match.score,
        decision.final_reason,
        candidate_price=candidate_price(match.data),
    )


async def _search(settings, verifier, item, decision):
    from .order_ai_matching import OrderAiOutcome

    result = await verifier.find_better_match(item.name, ai_candidates(decision))
    if not result or not result.get("record"):
        return None
    confidence = float(result.get("confidence", 0.0) or 0.0)
    if confidence < settings.accept_confidence:
        return OrderAiOutcome(
            decision, "ai_low_confidence", str(result.get("reason", "")), confidence, True
        )
    match = match_from_record(result["record"], result.get("score", 0.0))
    reviewed = await _review(settings, verifier, item, match, confidence, result)
    if reviewed:
        return reviewed
    active = MatchDecision(match, decision.diagnostics, "ai_search_accepted")
    return OrderAiOutcome(
        active, "ai_search_accepted", str(result.get("reason", "")), confidence
    )


async def _review(settings, verifier, item, match, confidence, result):
    from .order_ai_matching import OrderAiOutcome

    if not settings.api_config.review_model:
        return None
    review = await _review_match(verifier, item, match, confidence, result)
    review_conf = float(review.get("confidence", confidence) or 0.0)
    if review.get("is_correct") and review_conf >= settings.review_threshold:
        return None
    reason = str(review.get("reason", "review_rejected"))
    return OrderAiOutcome(
        MatchDecision(None, [], reason),
        "ai_review_rejected",
        reason,
        review_conf,
        True,
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
