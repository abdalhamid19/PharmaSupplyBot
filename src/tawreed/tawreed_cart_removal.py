"""Tawreed cart item removal flow."""

from __future__ import annotations
from typing import Iterable
from playwright.sync_api import Page
from ..core.cart_removal_items import CartRemovalItem, cart_row_matches_names
from ..core.cart_removal_summary import CartRemovalSummary, append_cart_removal_summary
from ..core.utils.excel import Item
from .tawreed_constants import VISIBLE_DIALOG_SELECTOR
from .tawreed_products_flow import require_product_match

def remove_items_from_cart(bot, page: Page, targets: list[any]) -> None:
    """Iterate through the cart and remove rows matching the requested items."""
    if not targets:
        bot.log("No cart items identified for removal.")
        return
    for target in targets:
        _process_removal_target(bot, page, target)

def _process_removal_target(bot, page, target):
    """Execute removal for one target and record results."""
    try:
        count = _remove_matching_rows(bot, page, target)
        status = "removed" if count else "not-found"
        reason = f"Removed {count} matching row(s)." if count else "No matching rows found."
    except Exception as error:
        count, status, reason = 0, "failed", str(error)
    append_cart_removal_summary(
        bot.profile_key, target.item,
        CartRemovalSummary(removed_count=count, status=status, reason=reason)
    )
    bot.log(f"Cart removal {target.item.code} / {target.item.name}: {reason}")

def _remove_matching_rows(bot, page, target) -> int:
    """Locate and delete matching cart rows."""
    count = 0
    while True:
        idx = _find_row_idx(page, target, bot.selectors.cart_rows)
        if idx is None: return count
        row = page.locator(bot.selectors.cart_rows).nth(idx)
        row.locator(bot.selectors.cart_delete_button).click()
        page.locator(bot.selectors.cart_confirm_delete).click()
        page.wait_for_timeout(1000)
        count += 1

def _find_row_idx(page, target, selector) -> int | None:
    """Return the first cart row index matching the removal item."""
    rows = page.locator(selector)
    for i in range(rows.count()):
        try: text = rows.nth(i).inner_text(timeout=500)
        except Exception: continue
        if cart_row_matches_names(text, target.names): return i
    return None

def resolve_cart_removal_targets(bot, page, items: Iterable[CartRemovalItem]):
    """Resolve Tawreed product names for removal items."""
    targets = []
    for item in items:
        names = [item.name]
        try:
            it = Item(code=item.code, name=item.name, qty=1)
            match, _ = require_product_match(bot, page, it)
            names.extend([
                str(match.data.get(k) or "")
                for k in ("productName", "productNameAr", "productNameEn")
            ])
        except Exception as e:
            bot.log(f"Could not resolve name for {item.name}: {e}")
        targets.append(_Target(item, _unique(names)))
    return targets

def _unique(names: list[str]) -> list[str]:
    res, seen = [], set()
    for n in names:
        t = str(n or "").strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            res.append(t)
    return res

class _Target:
    def __init__(self, item, names):
        self.item, self.names = item, names
