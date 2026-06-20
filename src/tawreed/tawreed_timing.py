"""Small helpers for per-item Tawreed runtime timings."""

from __future__ import annotations


TIMING_KEYS = (
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


def record_timing(bot, key: str, elapsed_seconds: float) -> None:
    """Accumulate one timing bucket on the current bot item state."""
    if key not in TIMING_KEYS:
        return
    timings = getattr(bot, "last_item_timings", None)
    if timings is None:
        timings = {}
        try:
            bot.last_item_timings = timings
        except AttributeError:
            return
    timings[key] = float(timings.get(key, 0.0)) + max(0.0, float(elapsed_seconds))


def timing_summary_fields(timings: dict[str, float] | None) -> dict[str, float]:
    """Return rounded timing fields suitable for summary artifacts."""
    values = timings or {}
    return {key: round(float(values.get(key, 0.0)), 3) for key in TIMING_KEYS}
