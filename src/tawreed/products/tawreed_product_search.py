"""DOM-backed Tawreed product table search helpers."""

from __future__ import annotations
import logging
logger = logging.getLogger(__name__)


import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..tawreed_constants import PRODUCT_SEARCH_ENDPOINT
from .tawreed_product_payloads import product_candidates_from_payload
from .tawreed_product_search_select import has_orderable_candidate, select_search_candidates
from ..matching.tawreed_timing import record_timing

PRODUCT_SEARCH_INPUT_SELECTOR = (
    "#tawreedTableGlobalSearch, "
    "input[name='tawreedTableGlobalSearch'], "
    "input[type='search'], "
    "input[placeholder*='بحث'], "
    "input[placeholder*='Search']"
)
def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search products and prefer API candidates over DOM fallbacks."""
    bot.log(f"Searching for '{query}'...")
    api_candidates = _execute_api_search(bot, page, query)
    
    if api_candidates is not None and has_orderable_candidate(api_candidates):
        return api_candidates
    
    return _execute_dom_fallback(bot, page, query, api_candidates)


def _execute_api_search(bot, page, query):
    from ..tawreed_dialogs import close_visible_dialogs
    started_at = time.perf_counter()
    close_visible_dialogs(page)
    record_timing(bot, "dialog_close_seconds", time.perf_counter() - started_at)
    started_at = time.perf_counter()
    api_candidates = _submit_product_search_with_api(page, query)
    record_timing(bot, "api_search_seconds", time.perf_counter() - started_at)
    return api_candidates


def _execute_dom_fallback(bot, page, query, api_candidates):
    from ..tawreed_dom import dom_search_results
    from ..tawreed_ui import is_no_results_row
    from ..matching.tawreed_timing import wait_for_table_overlay_to_clear

    started_at = time.perf_counter()
    wait_for_table_overlay_to_clear(page)
    rows = _ready_product_rows(page)
    record_timing(bot, "dom_wait_seconds", time.perf_counter() - started_at)
    if rows is None or is_no_results_row(rows.first):
        return select_search_candidates(api_candidates, [])
    return select_search_candidates(api_candidates, dom_search_results(page, query))


def _submit_product_search_with_api(page: Page, query: str) -> list[dict[str, Any]] | None:
    try:
        pattern = _search_response_pattern()
        with page.expect_response(pattern, timeout=2000) as resp:
            _submit_product_search(page, query)
        return _api_candidates(resp.value.json())
    except Exception:
        logger.debug("products._submit_product_search_with_api: API submit failed (non-fatal)")
        return None

def _search_response_pattern():
    return re.compile(f".*{PRODUCT_SEARCH_ENDPOINT}.*")

def _api_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep the historical browser-search helper name for callers."""
    return product_candidates_from_payload(payload)


def _submit_product_search(page: Page, query: str) -> None:
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    search.fill(query)
    search.press("Enter")


def _ready_product_rows(page: Page):
    from ..tawreed_ui import visible_product_rows
    rows = visible_product_rows(page)
    try:
        rows.first.wait_for(timeout=1500)
    except Exception:
        logger.debug("products._ready_product_rows: ready check failed (non-fatal)")
        return None
    return rows if rows.count() > 0 else None
