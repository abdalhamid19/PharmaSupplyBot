"""Tawreed cart item removal flow."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from .cart_removal_items import CartRemovalItem, cart_row_matches_item
from .cart_removal_summary import CartRemovalSummary, append_cart_removal_summary
from .tawreed_constants import VISIBLE_DIALOG_SELECTOR


@dataclass(frozen=True)
class CartRemovalSelectors:
    """Selectors used by the Tawreed cart-removal flow."""

    rows: str
    delete_button: str
    confirm_delete_button: str


def remove_items_from_cart(
    bot,
    page: Page,
    items: list[CartRemovalItem],
) -> None:
    """Remove all matching cart rows for each requested item."""
    selectors = CartRemovalSelectors(
        rows=bot.selectors.cart_rows,
        delete_button=bot.selectors.cart_delete_button,
        confirm_delete_button=bot.selectors.cart_confirm_delete_button,
    )
    for item in items:
        try:
            removed_count = remove_matching_cart_rows(page, item, selectors)
            status = "removed" if removed_count else "not-found"
            reason = (
                f"Removed {removed_count} matching cart row(s)."
                if removed_count
                else "No matching cart rows found."
            )
        except Exception as error:
            removed_count = 0
            status = "failed"
            reason = str(error)
        append_cart_removal_summary(
            bot.profile_key,
            item,
            CartRemovalSummary(
                removed_count=removed_count,
                status=status,
                reason=reason,
            ),
        )
        print(f"[{bot.profile_key}] Cart removal {item.code} / {item.name}: {reason}")


def remove_matching_cart_rows(
    page: Page,
    item: CartRemovalItem,
    selectors: CartRemovalSelectors,
) -> int:
    """Remove matching cart rows until no matching row remains."""
    removed_count = 0
    while True:
        row_index = first_matching_cart_row_index(page, item, selectors.rows)
        if row_index is None:
            return removed_count
        row = page.locator(selectors.rows).nth(row_index)
        delete_button = row.locator(selectors.delete_button).first
        delete_button.click(timeout=5000)
        confirm_delete_if_needed(page, selectors.confirm_delete_button)
        wait_for_cart_after_delete(page, selectors.rows)
        removed_count += 1


def first_matching_cart_row_index(page: Page, item: CartRemovalItem, rows_selector: str) -> int | None:
    """Return the first cart row index matching the removal item."""
    rows = page.locator(rows_selector)
    for row_index in range(rows.count()):
        row_text = rows.nth(row_index).inner_text(timeout=1500)
        if cart_row_matches_item(row_text, item):
            return row_index
    return None


def confirm_delete_if_needed(page: Page, confirm_delete_button_selector: str) -> None:
    """Confirm a delete dialog when Tawreed opens one."""
    dialog = page.locator(VISIBLE_DIALOG_SELECTOR)
    try:
        if dialog.count() == 0:
            return
    except Exception:
        return
    confirm_button = dialog.locator(confirm_delete_button_selector).first
    try:
        confirm_button.click(timeout=3000)
    except Exception:
        pass


def wait_for_cart_after_delete(page: Page, rows_selector: str) -> None:
    """Wait briefly for the cart table to settle after deleting a row."""
    try:
        page.locator(rows_selector).first.wait_for(timeout=1500)
    except Exception:
        pass
