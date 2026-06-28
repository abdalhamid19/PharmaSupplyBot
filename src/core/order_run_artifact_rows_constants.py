"""Constants for order run artifact rows."""

from __future__ import annotations

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

__all__ = ["REVIEWABLE_STATUSES", "SUMMARY_TIMING_KEYS"]
