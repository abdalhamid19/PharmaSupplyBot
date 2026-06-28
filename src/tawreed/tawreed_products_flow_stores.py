"""Store selection and add-to-cart logic for Tawreed products flow."""

import re
from typing import Any

from playwright.sync_api import Page

from ..core.matching_types import SearchMatch
from ..core.utils.excel import Item
from .tawreed_constants import STORE_DETAILS_ENDPOINT
from .tawreed_dialogs import close_visible_dialogs
from .tawreed_selections import stores_from_payload
from .tawreed_store_selection import choose_next_store_for_remaining_quantity
from .tawreed_ui import cart_button, stores_button, visible_dialog, store_dialog_cart_buttons
from .tawreed_waits import wait_for_row_to_settle
from .tawreed_products_flow_discount import (
    _wh_mode,
    _min_disc,
    _preferred_warehouses,
    _effective_min_discount,
    _find_max_discount,
)
from .tawreed_products_flow_dialog import fill_add_to_cart_dialog
from .tawreed_store_summary import record_single_store, record_selected_stores
from .tawreed_pricing import discount_value_as_percent, first_discount_value


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
