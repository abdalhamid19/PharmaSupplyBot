"""Structured rows for deterministic order-run artifacts."""

from __future__ import annotations

from ..manual_review.manual_review_reason import manual_review_reason_fields
from ..manual_review.manual_review_runtime import saved_manual_review_decision
from .order_winner_fields import candidate_summary_fields

REVIEWABLE_STATUSES = {
    "no-results", "matched-but-unavailable", "not-orderable",
    "manual-review-required", "manufacturer-mismatch",
}
SUMMARY_TIMING_KEYS = (
    "api_context_init_seconds", "api_search_seconds", "dom_wait_seconds",
    "dialog_close_seconds", "manual_review_lookup_seconds",
    "match_decision_seconds", "add_to_cart_seconds", "artifact_write_seconds",
    "summary_build_seconds",
)


def text_block(title: str, row: dict[str, object]) -> str:
    """Return one readable text block for an artifact row."""
    return f"\n--- {title} ---\n" + "\n".join(
        f"{key}={value}" for key, value in row.items()
    ) + "\n"


def manual_review_required(item, summary_status: str, config=None) -> bool:
    """Return whether the local result should be sent to manual review."""
    saved = saved_manual_review_decision(item)
    if saved and saved.manual_decision == "not_matching":
        return False
    if saved and saved.manual_decision in {"auto_matched", "approved_match"}:
        key = (
            "enable_auto_match_re_review_on_fail"
            if saved.manual_decision == "auto_matched"
            else "enable_approved_match_re_review_on_fail"
        )
        return bool(summary_status in REVIEWABLE_STATUSES and config and getattr(config, key, False))
    return summary_status in REVIEWABLE_STATUSES


def _candidate_for_summary(decision) -> tuple[object | None, dict]:
    match = getattr(decision, "best_match", None) if decision else None
    if match:
        return match, match.data
    diagnostics = getattr(decision, "diagnostics", []) if decision else []
    best = max(diagnostics, key=lambda item: item.score, default=None)
    return None, dict(getattr(best, "candidate", {}) or {})


def _timing_fields(summary) -> dict[str, float]:
    timings = getattr(summary, "timing_seconds", None) or {}
    return {
        "elapsed_seconds": round(float(getattr(summary, "elapsed_seconds", 0.0)), 3),
        "match_elapsed_seconds": round(float(getattr(summary, "match_elapsed_seconds", 0.0)), 3),
        **{key: round(float(timings.get(key, 0.0)), 3) for key in SUMMARY_TIMING_KEYS},
    }


def order_item_summary_row(item, summary, decision, config=None) -> dict[str, object]:
    """Return a compact row describing one deterministic order result."""
    match, candidate = _candidate_for_summary(decision)
    status = summary.status
    review = manual_review_required(item, status, config)
    query = match.query if match else ""
    score = round(float(match.score), 6) if match else ""
    row = {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "status": status,
        "reason": summary.reason,
        "ordered_total_qty": getattr(summary, "ordered_total_qty", ""),
        "matched_query": query,
        "deterministic_score": score,
        "matched": bool(match) and not review,
        "deterministic_match_found": bool(match),
        "manual_review_blocked_match": bool(match) and review,
        "manual_review_required": review,
    }
    row.update(candidate_summary_fields(candidate, decision, match, summary=summary))
    row.update(manual_review_reason_fields(status, summary.reason))
    row.update(_timing_fields(summary))
    return row


def manual_review_row(item, summary, decision, config=None) -> dict[str, object]:
    """Return an order row extended with empty human-review fields."""
    row = order_item_summary_row(item, summary, decision, config)
    row.update({
        "manual_review_reason_code": row["manual_review_category"] or row["status"],
        "manual_decision": "",
        "manual_reason": "",
        "correct_store_product_id": "",
    })
    return row


__all__ = [
    "order_item_summary_row", "manual_review_required", "manual_review_row",
    "text_block", "REVIEWABLE_STATUSES", "SUMMARY_TIMING_KEYS",
]
