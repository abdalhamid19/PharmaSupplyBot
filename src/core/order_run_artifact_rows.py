"""Structured rows for order item summary artifacts."""
from __future__ import annotations

from .manual_review_reason import manual_review_reason_fields
from .order_winner_fields import candidate_summary_fields

REVIEWABLE_STATUSES = {
    "no-results", "matched-but-unavailable", "not-orderable", "manual-review-required",
}


def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None
    candidate = match.data if match else {}
    row = {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": summary.status,
        "reason": summary.reason,
        "matched_query": match.query if match else "",
        "deterministic_score": round(match.score, 6) if match else "",
        **_match_state_fields(summary.status, outcome, match),
        **candidate_summary_fields(candidate, decision, match),
        **_summary_ai_fields(outcome, summary.status),
        **manual_review_reason_fields(summary.status, summary.reason, outcome),
    }
    return row


def manual_review_required(summary_status: str, outcome) -> bool:
    """Return whether this final item state needs human review."""
    if outcome is not None and outcome.manual_review:
        return True
    return summary_status in REVIEWABLE_STATUSES


def manual_review_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return a manual-review row with empty human decision columns."""
    row = order_item_summary_row(item, summary, decision, outcome)
    row.update(
        {
            "manual_review_reason_code": _manual_review_reason_code(summary.status, outcome),
            "manual_decision": "",
            "manual_reason": "",
            "correct_store_product_id": "",
        }
    )
    return row


def _match_state_fields(summary_status: str, outcome, match) -> dict[str, object]:
    return {
        "matched": _final_actionable_match(summary_status, outcome, match),
        "deterministic_match_found": bool(match),
        "manual_review_blocked_match": bool(match)
        and manual_review_required(summary_status, outcome),
    }


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for a structured artifact row."""
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"


def _summary_ai_fields(outcome, summary_status: str) -> dict[str, object]:
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
        "manual_review_required": manual_review_required(summary_status, outcome),
        "final_action": _final_action(summary_status, outcome),
    }


def _first_value(results, key: str) -> object:
    return next((result.get(key, "") for result in results if result.get(key)), "")

def _manual_review_reason_code(summary_status: str, outcome) -> str:
    status = getattr(outcome, "status", "") if outcome is not None else ""
    return status or summary_status

def _final_action(summary_status: str, outcome) -> str:
    return "manual_review" if manual_review_required(summary_status, outcome) else summary_status

def _final_actionable_match(summary_status: str, outcome, match) -> bool:
    return bool(match) and not manual_review_required(summary_status, outcome)
