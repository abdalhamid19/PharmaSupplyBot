"""DOM-backed Tawreed product table search helpers."""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

PRODUCT_SEARCH_INPUT_SELECTOR = (
    "#tawreedTableGlobalSearch, "
    "input[name='tawreedTableGlobalSearch'], "
    "input[type='search'], "
    "input[placeholder*='بحث'], "
    "input[placeholder*='Search']"
)


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search products and prefer API candidates over DOM fallbacks."""
    from .tawreed_dialogs import close_visible_dialogs
    from .tawreed_dom_parsing import dom_search_results
    from .tawreed_ui import is_no_results_row
    from .tawreed_waits import wait_for_table_overlay_to_clear

    bot.log(f"Searching for '{query}'...")
    close_visible_dialogs(page)
    api_candidates = _submit_product_search_with_api(page, query)
    wait_for_table_overlay_to_clear(page)
    if api_candidates is not None:
        return api_candidates
    rows = _ready_product_rows(page)
    if rows is None or is_no_results_row(rows.first):
        return []
    return dom_search_results(page, query)


def _submit_product_search_with_api(
    page: Page, query: str
) -> list[dict[str, Any]] | None:
    """Submit one product search and return API candidates when captured."""
    try:
        with page.expect_response(_search_response_pattern(), timeout=3000) as resp:
            _submit_product_search(page, query)
        return _api_candidates(resp.value.json())
    except Exception:
        return None


def _search_response_pattern():
    """Return the API response URL pattern for Tawreed product search."""
    return re.compile(f".*{PRODUCT_SEARCH_ENDPOINT}.*")


def _api_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return product candidates from a Tawreed search API payload."""
    return list(payload.get("data", []) or [])


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
