"""Products-page search and add-to-cart flow for Tawreed ordering."""

from __future__ import annotations
import time
from typing import Any
from playwright.sync_api import Page
from ..core.utils.excel import Item
from ..core.matching_models import MatchDecision, SearchMatch
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from .tawreed_match_logs import write_match_log
from .tawreed_ui import (
    cart_button, fill_quantity_input, store_dialog_cart_buttons,
    visible_dialog, stores_button, visible_product_rows, is_no_results_row
)
from .tawreed_search_logic import require_product_match
from .tawreed_store_selection import choose_next_store_for_remaining_quantity
from .tawreed_dialogs import close_visible_dialogs
from .tawreed_dom_parsing import dom_search_results
from .tawreed_waits import wait_for_table_overlay_to_clear, wait_for_row_to_settle
from .tawreed_selections import stores_from_payload
from .tawreed_constants import MAX_DOM_SEARCH_ROWS, STORE_DETAILS_ENDPOINT

def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    match, active_query = require_product_match(bot, page, item)
    row = matched_product_row(bot, page, match, active_query)
    open_add_to_cart_for_match(bot, page, row, item, match)

def matched_product_row(bot, page: Page, match: SearchMatch, active_query: str | None):
    """Re-run winning query and return the visible row corresponding to the match."""
    if active_query != match.query: search_products(bot, page, match.query)
    wait_for_table_overlay_to_clear(page)
    rows = visible_product_rows(page)
    row = _matched_row_by_sig(rows, match)
    if row is not None: return row
    if rows.count() <= match.row_index: raise RuntimeError(f"Missing row {match.row_index}")
    row = rows.nth(match.row_index)
    if is_no_results_row(row): raise RuntimeError(f"No results for '{match.query}'.")
    return row

def open_add_to_cart_for_match(bot, page: Page, row, item: Item, match: SearchMatch) -> None:
    """Open add-to-cart dialog for the selected match."""
    is_multi = int(match.data.get("productsCount") or 0) > 0
    if _is_dom_store(match): is_multi = False
    if is_multi:
        try: return add_item_from_store_dialogs(bot, page, row, item)
        except bot.skip_item_exception: raise
        except Exception:
            if not _cart_enabled(row): raise
            close_visible_dialogs(page)
    _click_cart(bot, row, item, match)
    bot.last_ordered_total_qty = fill_add_to_cart_dialog(bot, page, item.qty)

def add_item_from_store_dialogs(bot, page: Page, row, item: Item) -> None:
    """Add requested quantity across stores until fulfilled."""
    rem, used_ids, sels = int(item.qty), set(), []
    while rem > 0:
        store_rows = open_stores_dialog(bot, page, row)
        try:
            choice = _next_store_choice(bot, page, store_rows, used_ids, sels)
        except bot.skip_item_exception:
            if sels: break
            raise
        if choice is None: break
        ordered = fill_add_to_cart_dialog(bot, page, min(rem, choice.available_quantity))
        sels.append((choice.store, ordered))
        used_ids.add(choice.identity)
        rem -= ordered
    if not sels: raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)

def _next_store_choice(bot, page, store_rows, used_ids, sels):
    """Return the next eligible store or None if supply is exhausted."""
    try:
        choice = choose_next_store_for_remaining_quantity(
            store_rows, used_ids, _wh_mode(bot), bot.skip_item_exception, _min_disc(bot)
        )
        visible_dialog(page, bot.config.runtime.timeout_ms)
        store_dialog_cart_buttons(visible_dialog(page, 0)).nth(choice.index).click()
        return choice
    except bot.skip_item_exception:
        close_visible_dialogs(page)
        raise


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Execute a product search and return candidates from API or DOM."""
    bot.log(f"Searching for '{query}'...")
    search_input = page.locator("input[placeholder*='البحث']").first
    search_input.fill(query)
    with page.expect_response(re.compile(r".*/products/search.*"), timeout=2000) as resp:
        search_input.press("Enter")
        wait_for_table_overlay_to_clear(page)
        try:
            payload = resp.value.json()
            return list(payload.get("data", []) or [])
        except Exception:
            return dom_search_results(page, query)

def open_stores_dialog(bot, page: Page, row) -> list[dict[str, Any]]:
    """Open the stores dialog for a product and return store candidates."""
    with page.expect_response(re.compile(f".*{STORE_DETAILS_ENDPOINT}.*"), timeout=2000) as resp:
        stores_button(row).click()
        try: return stores_from_payload(resp.value.json())
        except Exception: return []

def fill_add_to_cart_dialog(bot, page: Page, requested_qty: int) -> int:
    """Fill the quantity dialog and return the actually ordered amount."""
    dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    qty = fill_quantity_input(dialog, requested_qty)
    dialog.locator("button:has-text('إضافة')").click()
    dialog.wait_for(state="hidden")
    return qty

def _is_dom_store(match: SearchMatch) -> bool:
    pid = str(match.data.get("storeProductId") or "")
    return pid.startswith("dom-row-") and match.data.get("discountPercent") not in (None, "")

def _cart_enabled(row) -> bool:
    try: return cart_button(row).is_enabled()
    except Exception: return False

def _click_cart(bot, row, item, match):
    wait_for_row_to_settle(row)
    cart_button(row).click()

def _matched_row_by_sig(rows, match: SearchMatch):
    sig = _normalize_sig(str(match.data.get("productName") or ""))
    if not sig: return None
    for i in range(min(rows.count(), MAX_DOM_SEARCH_ROWS)):
        row = rows.nth(i)
        if not is_no_results_row(row) and _row_sig(row) == sig: return row
    return None

def _row_sig(row) -> str:
    from .tawreed_dom_parsing import _row_name_lines
    lines = _row_name_lines(row)
    return _normalize_sig(lines[0]) if lines else ""

def _normalize_sig(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

def _wh_mode(bot): return bot.config.warehouse_strategy.get("mode", "highest_discount")
def _min_disc(bot): return float(bot.config.warehouse_strategy.get("min_discount_percent", 0))

def _record_stores(bot, sels):
    from .tawreed_store_selection import record_selected_stores
    record_selected_stores(bot, sels)
