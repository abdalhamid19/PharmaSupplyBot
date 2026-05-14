"""Review helpers for live-order AI matching."""
from __future__ import annotations

from .drug_matching.ai_provider_cooldown import apply_provider_cooldown
from .matching_models import MatchDecision
from .order_ai_records import candidate_ar, candidate_name


async def review_order_ai(settings, verifier, item, match, confidence, result):
    """Return a manual-review outcome when the review model rejects a match."""
    from .order_ai_matching import OrderAiOutcome

    if not settings.api_config.review_model:
        return None
    review = await _review_match(verifier, item, match, confidence, result)
    apply_provider_cooldown(verifier, review)
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
        review_result=review,
    )


def with_ai_results(outcome, **values):
    """Return an outcome copy with additional AI result dictionaries."""
    from .order_ai_matching import OrderAiOutcome

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
