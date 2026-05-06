"""DOM-backed Tawreed product table search helpers."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

PRODUCT_SEARCH_INPUT_SELECTOR = (
    "#tawreedTableGlobalSearch, "
    "input[name='tawreedTableGlobalSearch'], "
    "input[type='search'], "
    "input[placeholder*='بحث'], "
    "input[placeholder*='Search']"
)


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the products table and return the parsed DOM results."""
    from .tawreed_dialogs import close_visible_dialogs
    from .tawreed_dom_parsing import dom_search_results
    from .tawreed_ui import is_no_results_row
    from .tawreed_waits import wait_for_table_overlay_to_clear

    close_visible_dialogs(page)
    _submit_product_search(page, query)
    wait_for_table_overlay_to_clear(page)
    rows = _ready_product_rows(page)
    if rows is None or is_no_results_row(rows.first):
        return []
    return dom_search_results(page, query)


def _submit_product_search(page: Page, query: str) -> None:
    """Fill and submit the products-table search input."""
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    search.fill(query)
    search.press("Enter")


def _ready_product_rows(page: Page):
    """Return product rows when the table has rendered at least one row."""
    from .tawreed_ui import visible_product_rows

    rows = visible_product_rows(page)
    try:
        rows.first.wait_for(timeout=3000)
    except Exception:
        return None
    return rows if rows.count() > 0 else None
