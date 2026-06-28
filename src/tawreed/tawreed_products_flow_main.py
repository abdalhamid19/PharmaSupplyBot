"""Main products-page flow for Tawreed ordering."""

import time

from playwright.sync_api import Page

from ..core.matching_types import SearchMatch
from ..core.utils.excel import Item
from .tawreed_waits import wait_for_table_overlay_to_clear
from .tawreed_ui import is_no_results_row, visible_product_rows
from .tawreed_search_logic import require_product_match
from .tawreed_products_flow_stores import _open_add_to_cart_for_match
from .tawreed_products_flow_search import _matched_row_by_sig
from .tawreed_timing import record_timing


def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    match, active_query = require_product_match(bot, page, item)
    row = matched_product_row(bot, page, match, active_query)
    open_add_to_cart_for_match(bot, page, row, item, match)


def matched_product_row(bot, page: Page, match: SearchMatch, active_query: str | None):
    """Re-run winning query and return the visible row corresponding to the match."""
    from .tawreed_products_flow_search import search_visible_products_table
    from .tawreed_constants import MAX_DOM_SEARCH_ROWS
    
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
