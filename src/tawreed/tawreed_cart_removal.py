"""Tawreed cart item removal flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from playwright.sync_api import Page

from ..core.cart_removal_items import CartRemovalItem, cart_row_matches_names
from ..core.cart_removal_summary import CartRemovalSummary, append_cart_removal_summary
from ..core.utils.excel import Item
from .tawreed_constants import VISIBLE_DIALOG_SELECTOR
from .tawreed_products_flow import require_product_match


@dataclass(frozen=True)
class CartRemovalSelectors:
    """Selectors required to remove matching rows from the Tawreed cart."""

    cart_rows: str
    cart_delete_button: str
    cart_confirm_delete_button: str


@dataclass(frozen=True)
class CartRemovalTarget:
    """One cart-removal item plus every Tawreed name accepted for matching."""

    item: CartRemovalItem
    names: list[str]


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


def click_cart_delete_button(delete_button) -> None:
    """Click one cart-row delete button."""
    delete_button.click()


def confirm_delete_if_needed(page, selectors: CartRemovalSelectors) -> None:
    """Click the cart delete confirmation button when Tawreed shows one."""
    page.locator(selectors.cart_confirm_delete_button).click()


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


def resolve_cart_removal_targets(bot, page, items: Iterable[CartRemovalItem]):
    """Resolve Tawreed product names for removal items."""
    targets = []
    for item in items:
        if _cart_stop_requested(bot, item):
            break
        names = [item.name]
        try:
            it = Item(code=item.code, name=item.name, qty=1)
            match, _ = require_product_match(bot, page, it)
            names.extend(
                [
                    str(match.data.get(k) or "")
                    for k in ("productName", "productNameAr", "productNameEn")
                ]
            )
        except Exception as e:
            _log(bot, f"Could not resolve name for {item.name}: {e}")
        targets.append(CartRemovalTarget(item, _unique(names)))
    return targets


def _cart_stop_requested(bot, item: CartRemovalItem) -> bool:
    """Return whether cart-removal processing should stop before one item."""
    if not getattr(bot, "_stop_requested", lambda: False)():
        return False
    bot.log(f"Stop requested before cart item {item.code} / {item.name}.")
    return True


def _unique(names: list[str]) -> list[str]:
    """Return unique non-empty names while preserving original order."""
    res, seen = [], set()
    for n in names:
        t = str(n or "").strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            res.append(t)
    return res


def _log(bot, message: str) -> None:
    """Log through the bot when available, else print ASCII-safe text."""
    logger = getattr(bot, "log", None)
    if logger:
        logger(message)
        return
    print(message.encode("ascii", errors="replace").decode("ascii"))
