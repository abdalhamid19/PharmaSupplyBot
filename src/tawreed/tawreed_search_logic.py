"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page

from ..core.matching_models import SearchMatch
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_match_logs import write_match_log
from .tawreed_search_decision import decisive_match

PRODUCT_SEARCH_INPUT_SELECTOR = (
    "#tawreedTableGlobalSearch, "
    "input[name='tawreedTableGlobalSearch'], "
    "input[type='search'], "
    "input[placeholder*='بحث'], "
    "input[placeholder*='Search']"
)


def require_product_match(bot, page: Page, item: Item) -> tuple[SearchMatch, str]:
    """Search Tawreed using multiple query variants until a decisive match is found."""
    searched_queries: list[str] = []
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]] = []
    started_at = time.perf_counter()
    queries = _search_queries_for_item(item)

    for query_index, query in enumerate(queries):
        searched_queries.append(query)
        candidates = search_products(bot, page, query)
        search_results_by_query.append((query, candidates))

        decision = explain_best_product_match(
            item, search_results_by_query, bot.config.matching
        )
        if decisive_match(bot, item, decision, started_at, searched_queries):
            return decision.best_match, query

    # If no match found after all queries
    return _handle_no_match(bot, item, searched_queries, search_results_by_query)


def _handle_no_match(
    bot, item: Item, queries: list[str], results: list[tuple[str, list]]
):
    """Record and raise a descriptive error when all search attempts fail."""
    decision = explain_best_product_match(item, results, bot.config.matching)
    write_match_log(bot, item, decision)

    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(queries)} queries."
    )


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the products table and return the parsed API results for the query."""
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
