"""Core cart removal execution functions."""

from __future__ import annotations

from playwright.sync_api import Page

from ..core.cart_removal_items import CartRemovalItem
from ..core.cart_removal_summary import CartRemovalSummary, append_cart_removal_summary
from .tawreed_cart_removal_selectors import CartRemovalSelectors, CartRemovalTarget
from .tawreed_cart_removal_operations import _find_row_idx
from .tawreed_cart_removal_operations import click_cart_delete_button, confirm_delete_if_needed, _wait_after_cart_delete
from .tawreed_cart_removal_helpers import _cart_stop_requested, _log


def remove_items_from_cart(bot, page: Page, targets: list[CartRemovalTarget]) -> None:
    """Iterate through the cart and remove rows matching the requested items."""
    if not targets:
        bot.log("No cart items identified for removal.")
        return
    for target in targets:
        if _cart_stop_requested(bot, target.item):
            return
        _process_removal_target(bot, page, target)


def _process_removal_target(bot, page, target):
    """Execute removal for one target and record results."""
    try:
        count = _remove_matching_rows(bot, page, target)
        status = "removed" if count else "not-found"
        reason = (
            f"Removed {count} matching row(s)." if count else "No matching rows found."
        )
    except Exception as error:
        count, status, reason = 0, "failed", str(error)
    append_cart_removal_summary(
        bot.profile_key,
        target.item,
        CartRemovalSummary(removed_count=count, status=status, reason=reason),
        label_suffix=getattr(bot, "summary_label_suffix", None),
    )
    _log(bot, f"Cart removal {target.item.code} / {target.item.name}: {reason}")


def _remove_matching_rows(bot, page, target: CartRemovalTarget) -> int:
    """Locate and delete matching cart rows using the bot's selectors."""
    selectors = CartRemovalSelectors(
        bot.selectors.cart_rows,
        bot.selectors.cart_delete_button,
        bot.selectors.cart_confirm_delete_button,
    )
    return remove_matching_cart_rows(page, target, selectors)


def remove_matching_cart_rows(
    page, target: CartRemovalTarget, selectors: CartRemovalSelectors
) -> int:
    """Remove every visible cart row that matches the removal target."""
    count = 0
    while True:
        idx = _find_row_idx(page, target, selectors.cart_rows)
        if idx is None:
            return count
        count += _delete_cart_row(page, idx, selectors)


def _delete_cart_row(page, row_index: int, selectors: CartRemovalSelectors) -> int:
    """Delete one matching row and return whether it was removed."""
    rows = page.locator(selectors.cart_rows)
    before_count = rows.count()
    row = rows.nth(row_index)
    try:
        click_cart_delete_button(row.locator(selectors.cart_delete_button))
        confirm_delete_if_needed(page, selectors)
        _wait_after_cart_delete(page)
        return 1
    except Exception:
        if page.locator(selectors.cart_rows).count() < before_count:
            return 1
        raise


def _delete_cart_row(page, row_index: int, selectors: CartRemovalSelectors) -> int:
    """Delete one matching row and return whether it was removed."""
    rows = page.locator(selectors.cart_rows)
    before_count = rows.count()
    row = rows.nth(row_index)
    try:
        click_cart_delete_button(row.locator(selectors.cart_delete_button))
        confirm_delete_if_needed(page, selectors)
        _wait_after_cart_delete(page)
        return 1
    except Exception:
        if page.locator(selectors.cart_rows).count() < before_count:
            return 1
        raise


__all__ = [
    "remove_items_from_cart",
    "_process_removal_target",
    "_remove_matching_rows",
    "remove_matching_cart_rows",
    "_delete_cart_row",
]
