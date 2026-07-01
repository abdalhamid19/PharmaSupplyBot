"""AI status fields for order summary artifact rows."""

from __future__ import annotations


def summary_ai_fields(outcome, manual_review: bool, final_action: str) -> dict[str, object]:
    """Return compact AI columns for one order summary row."""
    verify = getattr(outcome, "verify_result", {}) or {}
    search = getattr(outcome, "search_result", {}) or {}
    review = getattr(outcome, "review_result", {}) or {}
    return {
        "ai_enabled": outcome is not None,
        "ai_status": getattr(outcome, "status", ""),
        "ai_verified": bool(verify),
        "ai_searched": bool(search),
        "ai_reviewed": bool(review),
        "ai_confidence": getattr(outcome, "confidence", ""),
        "ai_review_confidence": review.get("confidence", ""),
        "ai_model": _first_value((verify, search, review), "model_used"),
        "ai_provider": _first_value((verify, search, review), "provider_used"),
        "manual_review_required": manual_review,
        "final_action": final_action,
    }


def _first_value(results, key: str) -> object:
    return next((result.get(key, "") for result in results if result.get(key)), "")
