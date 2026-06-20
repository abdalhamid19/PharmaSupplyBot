"""Structured rows for order item summary artifacts."""
from __future__ import annotations

from .manual_review_reason import manual_review_reason_fields
from .order_blocked_candidate import (
    blocked_ai_candidate,
    blocked_candidate_fields,
    blocked_candidate_query,
    effective_order_status,
)
from .order_summary_ai_fields import summary_ai_fields
from .order_winner_fields import candidate_summary_fields

REVIEWABLE_STATUSES = {
    "no-results", "matched-but-unavailable", "not-orderable", "manual-review-required",
}


def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)
    manual_review = manual_review_required(item, status, outcome)
    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "matched_query": match.query if match else blocked_candidate_query(outcome),
        "deterministic_score": round(match.score, 6) if match else "",
        **_match_state_fields(item, status, outcome, match),
        **candidate_summary_fields(match.data if match else blocked_candidate, decision, match),
        **blocked_candidate_fields(blocked_candidate),
        **summary_ai_fields(outcome, manual_review, _final_action(status, manual_review)),
        **manual_review_reason_fields(status, summary.reason, outcome),
        "elapsed_seconds": round(float(getattr(summary, "elapsed_seconds", 0.0)), 3),
        "match_elapsed_seconds": round(
            float(getattr(summary, "match_elapsed_seconds", 0.0)), 3
        ),
        **_summary_timing_fields(summary),
    }


def manual_review_required(item, summary_status: str, outcome, config=None) -> bool:
    """Return whether this final item state needs human review."""
    from .manual_review_runtime import saved_manual_review_decision
    decision = saved_manual_review_decision(item)
    
    if decision and decision.manual_decision == "not_matching":
        return False
        
    if decision and decision.manual_decision == "auto_matched":
        if summary_status in REVIEWABLE_STATUSES:
            if config and getattr(config, "enable_auto_match_re_review_on_fail", False):
                return True # Drift detected! Item is missing, needs human eyes
        return False

    if decision and decision.manual_decision == "approved_match":
        if summary_status in REVIEWABLE_STATUSES:
            if config and getattr(config, "enable_approved_match_re_review_on_fail", False):
                return True # Out of stock! Item is missing, needs human eyes
        return False

    if outcome is not None and outcome.manual_review:
        return True
    
    return summary_status in REVIEWABLE_STATUSES


def manual_review_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return a manual-review row with empty human decision columns."""
    row = order_item_summary_row(item, summary, decision, outcome)
    row.update(
        {
            "manual_review_reason_code": _manual_review_reason_code(row["status"], outcome),
            "manual_decision": "",
            "manual_reason": "",
            "correct_store_product_id": "",
        }
    )
    return row


def _match_state_fields(item, summary_status: str, outcome, match) -> dict[str, object]:
    return {
        "matched": _final_actionable_match(item, summary_status, outcome, match),
        "deterministic_match_found": bool(match),
        "manual_review_blocked_match": bool(match)
        and manual_review_required(item, summary_status, outcome),
    }


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for a structured artifact row."""
    body = "\n".join(f"{key}={value}" for key, value in row.items())
    return f"\n--- {title} ---\n{body}\n"


def _manual_review_reason_code(summary_status: str, outcome) -> str:
    status = getattr(outcome, "status", "") if outcome is not None else ""
    return status or summary_status


def _final_action(summary_status: str, manual_review: bool) -> str:
    return "manual_review" if manual_review else summary_status


def _final_actionable_match(item, summary_status: str, outcome, match) -> bool:
    return bool(match) and not manual_review_required(item, summary_status, outcome)


def _summary_timing_fields(summary) -> dict[str, float]:
    timings = getattr(summary, "timing_seconds", None) or {}
    return {
        key: round(float(timings.get(key, 0.0)), 3)
        for key in (
            "api_search_seconds",
            "dom_wait_seconds",
            "dialog_close_seconds",
            "match_decision_seconds",
            "add_to_cart_seconds",
        )
    }
