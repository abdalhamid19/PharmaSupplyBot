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
SUMMARY_TIMING_KEYS = (
    "api_context_init_seconds",
    "api_search_seconds",
    "dom_wait_seconds",
    "dialog_close_seconds",
    "manual_review_lookup_seconds",
    "match_decision_seconds",
    "add_to_cart_seconds",
    "artifact_write_seconds",
    "summary_build_seconds",
)


def order_item_summary_row(item, summary, decision, outcome) -> dict[str, object]:
    """Return one compact row describing the final item outcome."""
    match = decision.best_match if decision else None
    blocked_candidate = blocked_ai_candidate(outcome) if not match else {}
    status = effective_order_status(summary.status, outcome)

    # Extract best diagnostic for not-orderable (FIX: removed blocked_candidate condition)
    best_diagnostic = None
    if status == "not-orderable" and not match:
        if decision and getattr(decision, "diagnostics", None):
            best_diagnostic = max(decision.diagnostics, key=lambda d: d.score, default=None)
            if best_diagnostic and getattr(best_diagnostic, "candidate", None):
                # Only fill if blocked_candidate is empty
                if not blocked_candidate:
                    blocked_candidate = best_diagnostic.candidate

    manual_review = manual_review_required(item, status, outcome)

    matched_query = match.query if match else blocked_candidate_query(outcome)
    if not matched_query and best_diagnostic:
        matched_query = best_diagnostic.query
        
    det_score = round(match.score, 6) if match else ""
    if not det_score and best_diagnostic:
        det_score = round(best_diagnostic.score, 6)

    # Use blocked_candidate as the match source for not-orderable
    match_source = match.data if match else blocked_candidate

    return {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "matched_query": matched_query,
        "deterministic_score": det_score,
        **_match_state_fields(item, status, outcome, match),
        **candidate_summary_fields(match_source, decision, match),
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
        for key in SUMMARY_TIMING_KEYS
    }
