"""Low-level cart removal operations."""

from __future__ import annotations

from playwright.sync_api import Page

from .tawreed_cart_removal_selectors import CartRemovalSelectors, CartRemovalTarget
from .tawreed_constants import VISIBLE_DIALOG_SELECTOR
from ..core.cart_removal_items import cart_row_matches_names


def click_cart_delete_button(delete_button) -> None:
    """Click one cart-row delete button."""
    delete_button.first.click()


def confirm_delete_if_needed(page, selectors: CartRemovalSelectors) -> None:
    """Click the cart delete confirmation button inside the visible dialog."""
    dialog = _visible_confirmation_dialog(page)
    if dialog is None:
        return
    dialog.locator(selectors.cart_confirm_delete_button).last.click(timeout=3000)


def _visible_confirmation_dialog(page):
    """Return the active PrimeNG dialog when a delete confirmation is visible."""
    dialogs = page.locator(VISIBLE_DIALOG_SELECTOR)
    try:
        if dialogs.count() > 0:
            return dialogs.last
    except Exception:
        return None
    return None


def _wait_after_cart_delete(page) -> None:
    """Wait briefly after deleting a cart row when the page supports waits."""
    if hasattr(page, "wait_for_timeout"):
        page.wait_for_timeout(1000)


def _find_row_idx(page, target, selector) -> int | None:
    """Return the first cart row index matching the removal item."""
    rows = page.locator(selector)
    for i in range(rows.count()):
        try:
            text = rows.nth(i).inner_text(timeout=500)
        except Exception:
            continue
        if cart_row_matches_names(text, target.names):
            return i
    return None


__all__ = [
    "click_cart_delete_button",
    "confirm_delete_if_needed",
    "_visible_confirmation_dialog",
    "_wait_after_cart_delete",
    "_find_row_idx",
]
