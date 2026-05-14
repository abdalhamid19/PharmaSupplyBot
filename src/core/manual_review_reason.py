"""Manual-review reason classification for order artifacts."""

from __future__ import annotations


def manual_review_reason_fields(
    summary_status: str, summary_reason: str, outcome
) -> dict[str, object]:
    """Return structured fields that explain why an item needs manual review."""
    category = _manual_review_category(summary_status, outcome)
    detail = _manual_review_detail(summary_reason, outcome)
    return {
        "manual_review_category": category,
        "manual_review_reason_detail": detail,
        "manual_review_blocking_phase": _blocking_phase(outcome, summary_status),
        "candidate_safety_reason": _candidate_safety_reason(outcome),
    }


def _manual_review_category(summary_status: str, outcome) -> str:
    status = str(getattr(outcome, "status", "") or summary_status)
    if summary_status == "matched-but-unavailable":
        return "matched_but_not_available"
    if summary_status == "not-orderable":
        return "candidate_not_orderable"
    if status == "ai_review_rejected":
        return "ai_review_rejected"
    if status == "ai_low_confidence":
        return "ai_low_confidence"
    if status == "ai_rejected":
        return "ai_rejected"
    if summary_status in {"no-results", "manual-review-required"}:
        return "no_decisive_match"
    return status or summary_status


def _manual_review_detail(summary_reason: str, outcome) -> str:
    detail = str(getattr(outcome, "reason", "") or summary_reason or "")
    verify = getattr(outcome, "verify_result", {}) or {}
    search = getattr(outcome, "search_result", {}) or {}
    review = getattr(outcome, "review_result", {}) or {}
    for result in (review, search, verify):
        reason = str(result.get("reason", "") or "")
        if reason and reason not in detail:
            return f"{detail} | {reason}" if detail else reason
    return detail


def _blocking_phase(outcome, summary_status: str) -> str:
    if outcome is None:
        return "summary_status" if summary_status else ""
    status = str(getattr(outcome, "status", "") or "")
    if status == "ai_review_rejected":
        return "ai_review"
    if status in {"ai_rejected", "ai_low_confidence"}:
        search = getattr(outcome, "search_result", {}) or {}
        verify = getattr(outcome, "verify_result", {}) or {}
        return "ai_search" if search else "ai_verify" if verify else "ai_final"
    if summary_status in {"matched-but-unavailable", "not-orderable"}:
        return "deterministic_match"
    return "summary_status"


def _candidate_safety_reason(outcome) -> str:
    for result in (
        getattr(outcome, "review_result", {}) or {},
        getattr(outcome, "search_result", {}) or {},
        getattr(outcome, "verify_result", {}) or {},
    ):
        reason = str(result.get("reason", "") or "")
        if reason.startswith("local_safety:"):
            return reason.removeprefix("local_safety:").strip()
        if "local safety" in reason.lower():
            return reason
    return ""
