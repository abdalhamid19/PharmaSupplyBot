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


def require_product_match(bot, page: Page, item: Item) -> tuple[SearchMatch, str]:
    """Search Tawreed using multiple query variants until a decisive match is found."""
    searched_queries: list[str] = []
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]] = []
    started_at = time.perf_counter()
    queries = _search_queries_for_item(item.name, item.code)

    for query_index, query in enumerate(queries):
        searched_queries.append(query)
        candidates = search_products(bot, page, query)
        search_results_by_query.append((query, candidates))
        
        decision = is_decisive_product_match(
            query, candidates, item.name, item.code, query_index=query_index
        )
        if _decisive_match(bot, item, decision, started_at, searched_queries):
            return decision.best_match, query

    # If no match found after all queries
    decision = is_decisive_product_match(
        searched_queries[-1], search_results_by_query[-1][1], 
        item.name, item.code, query_index=len(searched_queries)-1
    )
    write_match_log(bot, item, decision)
    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(searched_queries)} queries."
    )


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the products table and return the parsed API results for the query."""
    from .tawreed_products_flow import close_visible_dialogs, _wait_for_table_overlay_to_clear, wait_for_product_rows, _table_has_no_results, _dom_search_results
    
    close_visible_dialogs(page)
    search = page.locator(bot.selectors.item_search_input).first
    search.click()
    search.fill("")
    search.fill(query)
    search.press("Enter")
    _wait_for_table_overlay_to_clear(page)
    wait_for_product_rows(page)
    if _table_has_no_results(page):
        return []
    return _dom_search_results(page, query)


def _decisive_match(
    bot,
    item: Item,
    decision: MatchDecision,
    started_at: float,
    searched_queries: list[str],
) -> bool:
    """Return whether the current decision is final and record the outcome."""
    bot.last_match_decision = decision
    bot.last_searched_queries = searched_queries
    
    if not decision.best_match:
        if len(searched_queries) < MIN_SEARCH_QUERIES_PER_ITEM:
            return False
        write_match_log(bot, item, decision)
        # We don't raise here if we have more queries to try in require_product_match loop
        return False

    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    
    # Check availability
    available = decision.best_match.data.get("availableQuantity", 0)
    if available <= 0:
        raise bot.skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
        
    return True
