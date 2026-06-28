"""Search and row matching logic for Tawreed products flow."""

import re
import time
from typing import Any

from playwright.sync_api import Page

from ..core.matching_models import SearchMatch
from .tawreed_constants import MAX_DOM_SEARCH_ROWS
from .tawreed_dom_parsing import dom_search_results
from .tawreed_product_search import PRODUCT_SEARCH_INPUT_SELECTOR
from .tawreed_waits import wait_for_table_overlay_to_clear
from .tawreed_ui import is_no_results_row
from .tawreed_timing import record_timing


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
    from .tawreed_dom_parsing import _row_name_lines

    lines = _row_name_lines(row)
    return _normalize_sig(lines[0]) if lines else ""


def _normalize_sig(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())
