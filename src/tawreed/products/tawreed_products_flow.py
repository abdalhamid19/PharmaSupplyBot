"""Products-page search and add-to-cart flow for Tawreed ordering."""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

from src.core.matching_types import SearchMatch
from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate
from src.core.ordering.warehouse_order_policy import LOWEST_PURCHASE_PRICE_MODE
from src.core.utils.excel import Item
from ..tawreed_constants import MAX_DOM_SEARCH_ROWS, STORE_DETAILS_ENDPOINT
from ..tawreed_dialogs import close_visible_dialogs
from ..tawreed_dom import dom_search_results
from ..store.tawreed_pricing import discount_value_as_percent, first_discount_value
from .tawreed_product_search import PRODUCT_SEARCH_INPUT_SELECTOR
from ..api.tawreed_api_payloads import stores_from_payload
from ..store.tawreed_order_planning import plan_order_allocations
from ..store.tawreed_store_selection import (
    available_store_choices,
    choose_next_store_for_remaining_quantity,
)
from ..store.tawreed_store_summary import record_single_store, record_selected_stores
from ..store.tawreed_store_run_payload import (
    excel_target_cart_gate_run_key,
    persistence_options,
)
from ..tawreed_ui import (
    cart_button,
    fill_quantity_input,
    is_no_results_row,
    stores_button,
    store_dialog_cart_buttons,
    visible_dialog,
    visible_product_rows,
)
from ..matching.tawreed_timing import wait_for_row_to_settle, wait_for_table_overlay_to_clear, record_timing

# ============================================================================
# Discount and warehouse strategy helpers
# ============================================================================


def _wh_mode(bot):
    return LOWEST_PURCHASE_PRICE_MODE


def _min_disc(bot):
    return float(bot.config.warehouse_strategy.get("min_discount_percent", 0))


def _preferred_warehouses(bot) -> list[str]:
    return bot.config.warehouse_strategy.get("preferred_warehouses", [])


def _effective_min_discount(bot, sels) -> float:
    return _min_disc(bot)


def _cart_gate(bot) -> ExcelTargetCartGate:
    """Build the shared cart gate using this run's configured DB path."""
    options = persistence_options(bot) or {}
    return ExcelTargetCartGate(options.get("path"))


def _require_min_discount(bot, tawreed_store: dict[str, Any]) -> None:
    """Reject an ineligible Tawreed offer before selection or cart mutation."""
    minimum = _min_disc(bot)
    discount = max(
        0.0, discount_value_as_percent(first_discount_value(tawreed_store))
    )
    if discount < minimum - 0.001:
        raise bot.skip_item_exception(
            f"Tawreed offer discount {discount:g}% is below the configured "
            f"minimum {minimum:g}%."
        )


def _check_cart_gate(bot, item: Item, tawreed_store: dict[str, Any]) -> None:
    """Raise the bot's skip exception before a blocked cart mutation."""
    _require_min_discount(bot, tawreed_store)
    if getattr(bot, "match_only", False):
        return
    options = persistence_options(bot) or {}
    if not options.get("enabled", True):
        return
    decision = _cart_gate(bot).evaluate(
        excel_target_cart_gate_run_key(bot), item, tawreed_store
    )
    if decision.blocked:
        raise bot.skip_item_exception(
            f"Excel Target deferred_to_excel_target: {decision.reason}"
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
            logger.debug("products.search_visible_products_table: search failed (non-fatal)")
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
    from ..tawreed_dom import _row_name_lines

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
    _check_cart_gate(bot, item, match.data)
    _click_cart(bot, row, item, match)
    bot.last_ordered_total_qty = fill_add_to_cart_dialog(bot, page, item.qty)
    _record_single_store_selection(bot, match.data, bot.last_ordered_total_qty)


def add_item_from_store_dialogs(bot, page: Page, row, item: Item) -> None:
    """Add requested quantity across stores until fulfilled."""
    store_rows = open_stores_dialog(bot, page, row)
    plan = plan_order_allocations(
        bot,
        item,
        store_rows,
        mode=LOWEST_PURCHASE_PRICE_MODE,
        preferred_warehouses=_preferred_warehouses(bot),
        min_discount_percent=_min_disc(bot),
    )
    if plan.blocked_by_excel_target:
        raise bot.skip_item_exception(
            f"Excel Target deferred_to_excel_target: {plan.reason}; "
            f"{plan.excel_purchase_price:.2f}"
        )
    if not plan.allocations:
        raise bot.skip_item_exception("All stores out of stock or unpriced.")
    choices = available_store_choices(
        store_rows, None, _min_disc(bot), _preferred_warehouses(bot)
    )
    by_store = {id(choice.store): choice for choice in choices}
    actual_sels = []
    for line in plan.allocations:
        choice = by_store[id(line.store)]
        visible_dialog(page, bot.config.runtime.timeout_ms)
        store_dialog_cart_buttons(visible_dialog(page, 0)).nth(choice.index).click()
        actual_ordered = fill_add_to_cart_dialog(bot, page, line.quantity)
        actual_sels.append((choice.store, actual_ordered))
        bot.last_ordered_total_qty = sum(q for _, q in actual_sels)
        _record_stores(bot, actual_sels)


def _next_store_choice(bot, page, store_rows, used_ids, sels, *, click_cart: bool = True):
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
        if click_cart:
            visible_dialog(page, bot.config.runtime.timeout_ms)
            store_dialog_cart_buttons(visible_dialog(page, 0)).nth(choice.index).click()
        return choice
    except bot.skip_item_exception:
        close_visible_dialogs(page)
        raise


def open_stores_dialog(bot, page: Page, row) -> list[dict[str, Any]]:
    """Open the stores dialog for a product and return store candidates."""
    from ..store.tawreed_store_snapshot import SOURCE_STORE_DETAILS, record_store_rows

    with page.expect_response(
        re.compile(f".*{STORE_DETAILS_ENDPOINT}.*"), timeout=2000
    ) as resp:
        stores_button(row).click()
        try:
            stores = stores_from_payload(resp.value.json())
        except Exception:
            logger.debug("products.open_stores_dialog: open failed (non-fatal)")
            return []
        record_store_rows(bot, stores, SOURCE_STORE_DETAILS)
        return stores


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
        logger.debug("products._cart_enabled: check failed (non-fatal)")
        return False


def _click_cart(bot, row, item, match):
    _require_min_discount(bot, match.data)
    record_single_store(bot, match.data)
    _record_search_row_as_store(bot, match.data)
    wait_for_row_to_settle(row)
    cart_button(row).click()


def _record_search_row_as_store(bot, candidate: dict[str, Any]) -> None:
    """Record a single-store product from its search row.

    Products with ``productsCount == 0`` never open the stores dialog, so this
    is the only chance to capture their one offering store.
    """
    from ..store.tawreed_store_snapshot import SOURCE_SEARCH_ROW, record_store_rows

    record_store_rows(bot, [candidate], SOURCE_SEARCH_ROW)


def _record_single_store_selection(
    bot, candidate: dict[str, Any], ordered_qty: int
) -> None:
    """Record the one offering store as the selection for a single-store product.

    This path never opens the stores dialog, so ``_record_stores`` never runs and
    ``winner_store_key`` would stay unset even though a quantity was ordered.
    """
    from ..store.tawreed_store_snapshot import record_store_selections

    record_store_selections(bot, [(candidate, int(ordered_qty or 0))])


def _record_stores(bot, sels):
    from ..store.tawreed_store_snapshot import record_store_selections

    record_selected_stores(bot, sels)
    record_store_selections(bot, sels)


# ============================================================================
# Main products-page flow
# ============================================================================


def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    from ..matching.tawreed_search_logic import require_product_match

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
    "_record_search_row_as_store",
    "_record_single_store_selection",
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
    "_effective_min_discount",
    "_cart_gate",
    "_check_cart_gate",
    "_require_min_discount",
    # UI components (exported for external use)
    "cart_button",
    "visible_dialog",
    "wait_for_table_overlay_to_clear",
    "visible_product_rows",
    "store_dialog_cart_buttons",
    "wait_for_row_to_settle",
]
