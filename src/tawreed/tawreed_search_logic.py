"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import Any
from playwright.sync_api import Page

from ..core.utils.excel import Item
from ..core.matching_models import MatchDecision, SearchMatch
from ..core.product_matching import (
    _search_queries_for_item,
    explain_best_product_match,
    is_decisive_product_match,
)
from .tawreed_constants import PRODUCT_ROWS_SELECTOR
from .tawreed_match_logs import write_match_log

MIN_SEARCH_QUERIES_PER_ITEM = 3
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
        if _decisive_match(bot, item, decision, started_at, searched_queries):
            return decision.best_match, query

    # If no match found after all queries
    return _handle_no_match(bot, item, searched_queries, search_results_by_query)


def _handle_no_match(bot, item: Item, queries: list[str], results: list[tuple[str, list]]):
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
    from .tawreed_ui import is_no_results_row, visible_product_rows
    from .tawreed_waits import wait_for_table_overlay_to_clear
    
    close_visible_dialogs(page)
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    search.fill(query)
    search.press("Enter")
    wait_for_table_overlay_to_clear(page)
    rows = visible_product_rows(page)
    try:
        rows.first.wait_for(timeout=3000)
    except Exception:
        return []
    if rows.count() > 0 and is_no_results_row(rows.first):
        return []
    return dom_search_results(page, query)


def _decisive_match(
    bot, item: Item, decision: MatchDecision, started_at: float, queries: list[str]
) -> bool:
    """Return whether the current decision is final and record the outcome."""
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    if not decision.best_match:
        if len(queries) >= MIN_SEARCH_QUERIES_PER_ITEM: write_match_log(bot, item, decision)
        return False
    # Early stop check
    if getattr(bot, "fast_search", False):
        bot.last_match_elapsed_seconds = time.perf_counter() - started_at
        write_match_log(bot, item, decision)
        if decision.best_match.data.get("availableQuantity", 0) <= 0:
            raise bot.skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
        return True
    is_decisive = is_decisive_product_match(queries[-1], decision.best_match.data)
    if not is_decisive and len(queries) < MIN_SEARCH_QUERIES_PER_ITEM: return False
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    if decision.best_match.data.get("availableQuantity", 0) <= 0:
        raise bot.skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
    return True



