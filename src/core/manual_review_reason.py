"""Manual-review reason classification for order artifacts."""

from __future__ import annotations

from .order_blocked_candidate import candidate_safety_reason


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
        "candidate_safety_reason": candidate_safety_reason(outcome),
    }


def _manual_review_category(summary_status: str, outcome) -> str:
    status = str(getattr(outcome, "status", "") or summary_status)
    if candidate_safety_reason(outcome) == "missing storeProductId":
        return "candidate_not_orderable"
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
            detail = f"{detail} | {reason}" if detail else reason
            break
    # Append hard_conflicts from AI results if present
    conflicts = _collect_hard_conflicts(verify, search, review)
    if conflicts:
        conflict_text = f"hard_conflicts: {', '.join(conflicts)}"
        if conflict_text not in detail:
            detail = f"{detail} | {conflict_text}" if detail else conflict_text
    return detail


def _collect_hard_conflicts(*results: dict) -> list[str]:
    """Collect unique hard_conflicts from multiple AI result dicts."""
    seen: set[str] = set()
    out: list[str] = []
    for result in results:
        raw = result.get("hard_conflicts") or []
        if isinstance(raw, str):
            raw = [c.strip() for c in raw.split(",") if c.strip()]
        for conflict in raw:
            lower = conflict.lower()
            if lower not in seen:
                seen.add(lower)
                out.append(conflict)
    return out


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
