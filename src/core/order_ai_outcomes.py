"""Outcome builders for live-order AI flow."""
from __future__ import annotations

from .matching_models import MatchDecision


def low_confidence(decision, result, confidence, verify_result):
    """Return a manual-review outcome for low-confidence AI search."""
    from .order_ai_matching import OrderAiOutcome

    return OrderAiOutcome(
        decision, "ai_low_confidence", str(result.get("reason", "")),
        confidence, True, verify_result=verify_result, search_result=result,
    )


def accepted_search(decision, match, result, confidence, verify_result):
    """Return an accepted AI-search replacement outcome."""
    from .order_ai_matching import OrderAiOutcome

    active = MatchDecision(match, decision.diagnostics, "ai_search_accepted")
    return OrderAiOutcome(
        active, "ai_search_accepted", str(result.get("reason", "")), confidence,
        verify_result=verify_result, search_result=result,
    )


def rejected_search(decision, result, confidence, verify_result, reason):
    """Return a manual-review outcome for locally unsafe AI search."""
    from .order_ai_matching import OrderAiOutcome

    return OrderAiOutcome(
        decision,
        "ai_rejected",
        f"AI search candidate failed local safety: {reason}",
        confidence,
        True,
        verify_result=verify_result,
        search_result=result,
    )
