"""Tawreed cart item removal flow."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from .cart_removal_items import CartRemovalItem, cart_row_matches_names
from .cart_removal_summary import CartRemovalSummary, append_cart_removal_summary
from .excel import Item
from .tawreed_constants import VISIBLE_DIALOG_SELECTOR
from .tawreed_products_flow import require_product_match


@dataclass(frozen=True)
class CartRemovalSelectors:
    """Selectors used by the Tawreed cart-removal flow."""

    rows: str
    delete_button: str
    confirm_delete_button: str


@dataclass(frozen=True)
class CartRemovalTarget:
    """One removal item plus Tawreed names that may appear in the cart."""

    item: CartRemovalItem
    names: list[str]


def remove_items_from_cart(
    bot,
    page: Page,
    targets: list[CartRemovalTarget],
) -> None:
    """Remove all matching cart rows for each requested item."""
    selectors = CartRemovalSelectors(
        rows=bot.selectors.cart_rows,
        delete_button=bot.selectors.cart_delete_button,
        confirm_delete_button=bot.selectors.cart_confirm_delete_button,
    )
    for target in targets:
        item = target.item
        try:
            removed_count = remove_matching_cart_rows(page, target, selectors)
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


def resolve_cart_removal_targets(
    bot,
    page: Page,
    items: list[CartRemovalItem],
) -> list[CartRemovalTarget]:
    """Resolve Tawreed product names for removal items before scanning the cart."""
    targets: list[CartRemovalTarget] = []
    for item in items:
        names = [item.name]
        try:
            match, _ = require_product_match(bot, page, Item(code=item.code, name=item.name, qty=1))
            names.extend(tawreed_match_names(match.data))
        except Exception as error:
            print(f"[{bot.profile_key}] Could not resolve Tawreed name for {item.name}: {error}")
        targets.append(CartRemovalTarget(item=item, names=unique_names(names)))
    return targets


def tawreed_match_names(candidate: dict) -> list[str]:
    """Return Tawreed product names that can appear in cart rows."""
    return [
        str(candidate.get("productName") or ""),
        str(candidate.get("productNameAr") or ""),
        str(candidate.get("productNameEn") or ""),
    ]


def unique_names(names: list[str]) -> list[str]:
    """Return non-empty names without duplicates, preserving order."""
    unique: list[str] = []
    seen: set[str] = set()
    for name in names:
        text = str(name or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        unique.append(text)
    return unique


def remove_matching_cart_rows(
    page: Page,
    target: CartRemovalTarget,
    selectors: CartRemovalSelectors,
) -> int:
    """Remove matching cart rows until no matching row remains."""
    removed_count = 0
    while True:
        row_index = first_matching_cart_row_index(page, target, selectors.rows)
        if row_index is None:
            return removed_count
        row = page.locator(selectors.rows).nth(row_index)
        delete_button = row.locator(selectors.delete_button).first
        remove_one_matching_cart_row(page, target, selectors, delete_button)
        removed_count += 1


def remove_one_matching_cart_row(
    page: Page,
    target: CartRemovalTarget,
    selectors: CartRemovalSelectors,
    delete_button,
) -> None:
    """Remove one matched row and tolerate Tawreed DOM churn after successful clicks."""
    try:
        click_cart_delete_button(delete_button)
        confirm_delete_if_needed(page, selectors.confirm_delete_button)
        wait_for_cart_after_delete(page, selectors.rows)
        return
    except Exception:
        wait_for_cart_after_delete(page, selectors.rows)
        if first_matching_cart_row_index(page, target, selectors.rows) is None:
            return
        raise


def click_cart_delete_button(delete_button) -> None:
    """Click one cart delete button, forcing the click if overlays intercept it."""
    try:
        delete_button.click(timeout=5000)
        return
    except Exception:
        pass
    delete_button.click(timeout=5000, force=True)


def first_matching_cart_row_index(
    page: Page,
    target: CartRemovalTarget,
    rows_selector: str,
) -> int | None:
    """Return the first cart row index matching the removal item."""
    rows = page.locator(rows_selector)
    for row_index in range(rows.count()):
        row_text = rows.nth(row_index).inner_text(timeout=1500)
        if cart_row_matches_names(row_text, target.names):
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
