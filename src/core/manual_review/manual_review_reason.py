"""Manual-review reason classification for deterministic order artifacts."""

from __future__ import annotations


def manual_review_reason_fields(summary_status: str, summary_reason: str) -> dict[str, object]:
    """Return structured local reasons for a manual-review item."""
    category = _manual_review_category(summary_status)
    return {
        "manual_review_category": category,
        "manual_review_reason_detail": str(summary_reason or ""),
        "manual_review_blocking_phase": _blocking_phase(summary_status),
        "candidate_safety_reason": "missing storeProductId" if summary_status == "not-orderable" else "",
    }


def _manual_review_category(status: str) -> str:
    return {
        "matched-but-unavailable": "matched_but_not_available",
        "not-orderable": "candidate_not_orderable",
        "manufacturer-mismatch": "manufacturer_mismatch",
        "no-results": "no_decisive_match",
        "manual-review-required": "no_decisive_match",
    }.get(status, status)


def _blocking_phase(status: str) -> str:
    if status in {"matched-but-unavailable", "not-orderable", "manufacturer-mismatch"}:
        return "deterministic_match"
    return "summary_status" if status else ""


__all__ = ["manual_review_reason_fields"]
