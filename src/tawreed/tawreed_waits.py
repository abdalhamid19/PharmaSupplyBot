"""Wait and synchronization helpers for Tawreed UI transitions."""

from __future__ import annotations
from playwright.sync_api import Page
from .tawreed_constants import DIALOG_MASK_SELECTOR
from .tawreed_ui import cart_button

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
