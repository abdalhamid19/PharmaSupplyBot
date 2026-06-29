"""Products-page search and add-to-cart flow for Tawreed ordering."""

import re
import time
from typing import Any

from playwright.sync_api import Page

from ..core.matching_types import SearchMatch
from ..core.utils.excel import Item
from .tawreed_constants import MAX_DOM_SEARCH_ROWS, STORE_DETAILS_ENDPOINT
from .tawreed_dialogs import close_visible_dialogs
from .tawreed_dom import dom_search_results
from .tawreed_pricing import discount_value_as_percent, first_discount_value
from .tawreed_product_search import PRODUCT_SEARCH_INPUT_SELECTOR
from .tawreed_api_payloads import stores_from_payload
from .tawreed_store_selection import choose_next_store_for_remaining_quantity
from .tawreed_store_summary import record_single_store, record_selected_stores
from .tawreed_ui import (
    cart_button,
    fill_quantity_input,
    is_no_results_row,
    stores_button,
    store_dialog_cart_buttons,
    visible_dialog,
    visible_product_rows,
)
from .tawreed_timing import wait_for_row_to_settle, wait_for_table_overlay_to_clear, record_timing

# ============================================================================
# Discount and warehouse strategy helpers
# ============================================================================


def _wh_mode(bot):
    return bot.config.warehouse_strategy.get("mode", "first_available")


def _min_disc(bot):
    return float(bot.config.warehouse_strategy.get("min_discount_percent", 0))


def _preferred_warehouses(bot) -> list[str]:
    return bot.config.warehouse_strategy.get("preferred_warehouses", [])


def _find_max_discount(stores: list[dict[str, Any]]) -> float:
    """Find the maximum discount percent among available stores."""
    max_discount = 0.0
    for store in stores:
        if int(store.get("availableQuantity", 0) or 0) > 0:
            discount = discount_value_as_percent(first_discount_value(store))
            max_discount = max(max_discount, discount)
    return max_discount


def _effective_min_discount(bot, sels) -> float:
    if _wh_mode(bot) != "max_discount" or not sels:
        return _min_disc(bot)
    return max(_min_disc(bot), _selected_max_discount(sels))


def _selected_max_discount(sels) -> float:
    return max(
        discount_value_as_percent(first_discount_value(store)) for store, _ in sels
    )


# ============================================================================
# Add-to-cart dialog handling
# ============================================================================


def fill_add_to_cart_dialog(bot, page: Page, requested_qty: int) -> int:
    """Fill the quantity dialog and return the actually ordered amount."""
    dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    qty = fill_quantity_input(dialog, requested_qty)
    dialog.locator("button:has-text('إضافة')").click()
    dialog.wait_for(state="hidden")
    return qty


# ============================================================================
# Search and row matching logic
# ============================================================================


def search_visible_products_table(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the visible products table so the matched row can be clicked."""
    bot.log(f"Searching for '{query}'...")
    search_input = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search_input.fill(query)
    started_at = time.perf_counter()
    with page.expect_response(
        re.compile(r".*/products/search.*"), timeout=2000
    ) as resp:
        search_input.press("Enter")
        wait_for_table_overlay_to_clear(page)
        record_timing(bot, "api_search_seconds", time.perf_counter() - started_at)
        try:
            payload = resp.value.json()
            return list(payload.get("data", []) or [])
        except Exception:
            return dom_search_results(page, query)


def _matched_row_by_sig(rows, match: SearchMatch):
    sig = _normalize_sig(str(match.data.get("productName") or ""))
    if not sig:
        return None
    for i in range(min(rows.count(), MAX_DOM_SEARCH_ROWS)):
        row = rows.nth(i)
        if not is_no_results_row(row) and _row_sig(row) == sig:
            return row
    return None


def _row_sig(row) -> str:
    from .tawreed_dom import _row_name_lines

    lines = _row_name_lines(row)
    return _normalize_sig(lines[0]) if lines else ""


def _normalize_sig(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


# ============================================================================
# Store selection and add-to-cart logic
# ============================================================================


def _open_add_to_cart_for_match(
    bot, page: Page, row, item: Item, match: SearchMatch
) -> None:
    """Open add-to-cart dialog for the selected match."""
    is_multi = int(match.data.get("productsCount") or 0) > 0
    if _is_dom_store(match):
        is_multi = False
    if is_multi:
        try:
            return add_item_from_store_dialogs(bot, page, row, item)
        except bot.skip_item_exception:
            raise
        except Exception:
            if not _cart_enabled(row):
                raise
            close_visible_dialogs(page)
    _click_cart(bot, row, item, match)
    bot.last_ordered_total_qty = fill_add_to_cart_dialog(bot, page, item.qty)


def add_item_from_store_dialogs(bot, page: Page, row, item: Item) -> None:
    """Add requested quantity across stores until fulfilled."""
    rem, used_ids, sels = int(item.qty), set(), []
    store_rows = open_stores_dialog(bot, page, row)
    mode = _wh_mode(bot)
    
    max_discount_value = None
    if mode == "max_discount" and store_rows:
        max_discount_value = _find_max_discount(store_rows)
        min_discount = _min_disc(bot)
        if max_discount_value < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Highest discount ({max_discount_value:g}%) is below minimum ({min_discount:g}%)."
            )
    
    while rem > 0:
        try:
            choice = _next_store_choice(bot, page, store_rows, used_ids, sels)
        except bot.skip_item_exception:
            if sels:
                break
            raise
        if choice is None:
            break
        ordered = fill_add_to_cart_dialog(
            bot, page, min(rem, choice.available_quantity)
        )
        sels.append((choice.store, ordered))
        used_ids.add(choice.identity)
        rem -= ordered
        
        if mode == "max_discount" and max_discount_value is not None:
            if choice.discount_percent < max_discount_value - 0.5:
                break
            
    if not sels:
        raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)


def _next_store_choice(bot, page, store_rows, used_ids, sels):
    """Return the next eligible store or None if supply is exhausted."""
    try:
        choice = choose_next_store_for_remaining_quantity(
            store_rows,
            used_ids,
            _wh_mode(bot),
            bot.skip_item_exception,
            _effective_min_discount(bot, sels),
            _preferred_warehouses(bot),
        )
        if choice is None:
            close_visible_dialogs(page)
            return None
        visible_dialog(page, bot.config.runtime.timeout_ms)
        store_dialog_cart_buttons(visible_dialog(page, 0)).nth(choice.index).click()
        return choice
    except bot.skip_item_exception:
        close_visible_dialogs(page)
        raise


def open_stores_dialog(bot, page: Page, row) -> list[dict[str, Any]]:
    """Open the stores dialog for a product and return store candidates."""
    with page.expect_response(
        re.compile(f".*{STORE_DETAILS_ENDPOINT}.*"), timeout=2000
    ) as resp:
        stores_button(row).click()
        try:
            return stores_from_payload(resp.value.json())
        except Exception:
            return []


def _is_dom_store(match: SearchMatch) -> bool:
    pid = str(match.data.get("storeProductId") or "")
    return pid.startswith("dom-row-") and match.data.get("discountPercent") not in (
        None,
        "",
    )


def _cart_enabled(row) -> bool:
    try:
        return cart_button(row).is_enabled()
    except Exception:
        return False


def _click_cart(bot, row, item, match):
    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )
    
    record_single_store(bot, match.data)
    wait_for_row_to_settle(row)
    cart_button(row).click()


def _record_stores(bot, sels):
    record_selected_stores(bot, sels)


# ============================================================================
# Main products-page flow
# ============================================================================


def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    from .tawreed_search_logic import require_product_match
    
    match, active_query = require_product_match(bot, page, item)
    row = matched_product_row(bot, page, match, active_query)
    open_add_to_cart_for_match(bot, page, row, item, match)


def matched_product_row(bot, page: Page, match: SearchMatch, active_query: str | None):
    """Re-run winning query and return the visible row corresponding to the match."""
    if active_query != match.query:
        search_visible_products_table(bot, page, match.query)
    wait_for_table_overlay_to_clear(page)
    rows = visible_product_rows(page)
    row = _matched_row_by_sig(rows, match)
    if row is not None:
        return row
    if rows.count() <= match.row_index:
        raise RuntimeError(f"Missing row {match.row_index}")
    row = rows.nth(match.row_index)
    if is_no_results_row(row):
        raise RuntimeError(f"No results for '{match.query}'.")
    return row


def open_add_to_cart_for_match(
    bot, page: Page, row, item: Item, match: SearchMatch
) -> None:
    """Open add-to-cart dialog for the selected match."""
    started_at = time.perf_counter()
    try:
        _open_add_to_cart_for_match(bot, page, row, item, match)
    finally:
        record_timing(bot, "add_to_cart_seconds", time.perf_counter() - started_at)


__all__ = [
    # Main flow
    "add_item_from_products_page",
    "matched_product_row",
    "open_add_to_cart_for_match",
    # Store selection
    "add_item_from_store_dialogs",
    "open_stores_dialog",
    "_click_cart",
    "_record_stores",
    # Search
    "search_visible_products_table",
    "_matched_row_by_sig",
    # Dialog
    "fill_add_to_cart_dialog",
    # Discount helpers (exported for API flow)
    "_wh_mode",
    "_min_disc",
    "_preferred_warehouses",
    "_find_max_discount",
    "_effective_min_discount",
    "_selected_max_discount",
    # UI components (exported for external use)
    "cart_button",
    "visible_dialog",
    "wait_for_table_overlay_to_clear",
    "visible_product_rows",
    "store_dialog_cart_buttons",
    "wait_for_row_to_settle",
]
