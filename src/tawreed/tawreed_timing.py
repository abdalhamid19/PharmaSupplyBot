"""Small helpers for per-item Tawreed runtime timings and UI waits."""

from __future__ import annotations

from playwright.sync_api import Page

from .tawreed_constants import DIALOG_MASK_SELECTOR
from .tawreed_ui import cart_button


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


# ============================================================================
# Wait helpers (from tawreed_waits.py)
# ============================================================================

def wait_for_table_overlay_to_clear(page: Page) -> None:
    """Wait for Tawreed's table loading overlay to disappear."""
    try:
        page.locator(".p-datatable-loading-overlay").first.wait_for(state="hidden", timeout=2000)
    except Exception:
        pass


def wait_for_dialog_to_clear(page: Page) -> None:
    """Wait briefly for remaining visible dialog masks to disappear."""
    try:
        page.locator(DIALOG_MASK_SELECTOR).first.wait_for(state="hidden", timeout=1500)
    except Exception:
        pass


def wait_for_row_to_settle(row) -> None:
    """Wait briefly for a matched row's cart button to stop changing."""
    try:
        cart_button(row).wait_for(timeout=1500)
    except Exception:
        pass


__all__ = [
    # Timing
    "TIMING_KEYS",
    "record_timing",
    "timing_summary_fields",
    # Waits
    "wait_for_table_overlay_to_clear",
    "wait_for_dialog_to_clear",
    "wait_for_row_to_settle",
]
