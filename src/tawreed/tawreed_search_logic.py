"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page

from ..core.matching_models import SearchMatch
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_match_logs import write_match_log
from .tawreed_product_search import search_products
from .tawreed_search_decision import decisive_match


def require_product_match(
    bot, page: Page, item: Item, require_available: bool = True
) -> tuple[SearchMatch, str]:
    """Search Tawreed query variants until a decisive match is found."""
    queries: list[str] = []
    results: list[tuple[str, list[dict[str, Any]]]] = []
    started_at = time.perf_counter()

    for query in _search_queries_for_item(item):
        match = _search_one_query(
            bot, page, item, query, started_at, queries, results, require_available
        )
        if match:
            return match, query

    return _handle_no_match(bot, item, queries, results)


def _search_one_query(
    bot, page, item, query, started_at, queries, results, require_available
):
    """Search one query and return the final match when it is decisive."""
    queries.append(query)
    results.append((query, search_products(bot, page, query)))
    decision = explain_best_product_match(item, results, bot.config.matching)
    match = decision.best_match
    if not match:
        decisive_match(bot, item, decision, started_at, queries, require_available)
        return None
    is_final = decisive_match(
        bot, item, decision, started_at, queries, require_available
    )
    return match if is_final else None


def _handle_no_match(
    bot, item: Item, queries: list[str], results: list[tuple[str, list]]
):
    """Record and raise a descriptive error when all search attempts fail."""
    decision = explain_best_product_match(item, results, bot.config.matching)
    write_match_log(bot, item, decision)

    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(queries)} queries."
    )
