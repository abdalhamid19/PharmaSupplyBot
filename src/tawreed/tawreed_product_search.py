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
_PRODUCT_LIST_KEYS = ("data", "items", "products", "result", "results", "storeProducts")


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
    try:
        with page.expect_response(_search_response_pattern(), timeout=3000) as resp:
            _submit_product_search(page, query)
        return _api_candidates(resp.value.json())
    except Exception:
        return None


def _search_response_pattern(): return re.compile(f".*{PRODUCT_SEARCH_ENDPOINT}.*")


def _api_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]: return _product_dicts(payload)


def _product_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if _is_product_dict(item)]
    if not isinstance(value, dict):
        return []
    if _is_product_dict(value):
        return [value]
    return _first_nested_product_list(value)


def _first_nested_product_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _PRODUCT_LIST_KEYS:
        candidates = _product_dicts(payload.get(key))
        if candidates:
            return candidates
    return []


def _is_product_dict(value: Any) -> bool:
    return isinstance(value, dict) and bool(
        value.get("productName") or value.get("productNameEn")
    )


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
