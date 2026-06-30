"""PrimeNG dialog and overlay interaction helpers for Tawreed."""

from __future__ import annotations
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page, Locator

from .tawreed_ui import (
    dialog_close_buttons, visible_dialog, visible_dialog_masks, visible_overlay_panels
)
from .tawreed_constants import DIALOG_MASK_SELECTOR, OVERLAY_PANEL_SELECTOR

def close_visible_dialogs(page: Page) -> None:
    """Close visible dialogs and overlay panels so later items can continue safely."""
    try:
        while visible_dialog_masks(page).count() > 0:
            dialog = visible_dialog(page, 500)  # Reduced from 1000
            close_buttons = dialog_close_buttons(dialog)
            if close_buttons.count() > 0:
                close_buttons.first.click(force=True)
                dialog.wait_for(state="hidden", timeout=800)  # Reduced from 1500
                continue
            with suppress(Exception):
                visible_dialog_masks(page).last.click(force=True)
                dialog.wait_for(state="hidden", timeout=800)  # Reduced from 1500
                continue
            page.keyboard.press("Escape")
            dialog.wait_for(state="hidden", timeout=800)  # Reduced from 1500
    except Exception:
        pass
    close_visible_overlay_panels(page)

def close_visible_overlay_panels(page: Page) -> None:
    """Dismiss PrimeNG overlay panels that are not represented by dialog masks."""
    try:
        for _ in range(2):  # Reduced from 3
            if visible_overlay_panels(page).count() <= 0:
                return
            with suppress(Exception):
                page.keyboard.press("Escape")
            _wait_for_overlay_panels_to_clear(page, timeout_ms=300)  # Reduced from 500
        if visible_overlay_panels(page).count() > 0:
            _click_safe_page_area(page)
            _wait_for_overlay_panels_to_clear(page, timeout_ms=400)  # Reduced from 700
    except Exception:
        pass

def visible_overlay_diagnostics(page: Page) -> str:
    """Return compact diagnostics for visible dialogs and overlay panels."""
    lines: list[str] = []
    _append_visible_count(lines, "dialog_masks", f"{DIALOG_MASK_SELECTOR}:visible", page)
    _append_visible_count(lines, "overlay_panels", _visible_selector(OVERLAY_PANEL_SELECTOR), page)
    return "\n".join(lines)

def _wait_for_overlay_panels_to_clear(page: Page, timeout_ms: int) -> None:
    """Wait briefly for non-dialog overlay panels to disappear."""
    try:
        page.locator(OVERLAY_PANEL_SELECTOR).first.wait_for(state="hidden", timeout=timeout_ms)
    except Exception:
        pass

def _click_safe_page_area(page: Page) -> None:
    """Click outside overlays without depending on page-specific layout."""
    with suppress(Exception):
        page.locator("body").click(position={"x": 1, "y": 1}, force=True)
        return
    with suppress(Exception):
        page.mouse.click(1, 1)

def _append_visible_count(lines: list[str], label: str, selector: str, page: Page) -> None:
    """Append one visible-locator count line for failure artifacts."""
    try:
        count = page.locator(selector).count()
    except Exception as error:
        lines.append(f"{label}=unavailable ({type(error).__name__}: {error})")
        return
    lines.append(f"{label}={count}")

def _visible_selector(selector: str) -> str:
    """Add :visible to each selector in a comma-separated selector list."""
    return ", ".join(f"{part.strip()}:visible" for part in selector.split(",") if part.strip())
