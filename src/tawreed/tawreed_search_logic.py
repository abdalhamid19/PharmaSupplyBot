"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page

from ..core.manual_review_runtime import (
    filter_manual_review_candidates,
    manual_review_queries,
)
from ..core.matching_models import SearchMatch
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_match_logs import write_match_log
from .tawreed_aggressive_matching import aggressive_review_result
from .tawreed_match_acceptance import accepted_no_match_result
from .tawreed_manual_review_flow import manual_review_result
from .tawreed_product_search import search_products
from .tawreed_query_cache import cached_query_result
from .tawreed_search_decision import decisive_match


def require_product_match(
    bot, page: Page, item: Item, require_available: bool = True
) -> tuple[SearchMatch, str]:
    """Search Tawreed query variants until a decisive match is found."""
    queries: list[str] = []
    results: list[tuple[str, list[dict[str, Any]]]] = []
    query_cache: dict[str, list[dict[str, Any]]] = {}
    started_at = time.perf_counter()

    for query in manual_review_queries(item, _search_queries_for_item(item)):
        match = _search_one_query(
            bot, page, item, query, started_at,
            queries, results, query_cache, require_available,
        )
        if match:
            return match, query

    return _handle_no_match(bot, item, queries, results, require_available)


def _search_one_query(
    bot, page, item, query, started_at, queries, results, query_cache, require_available
):
    """Search one query and return the final match when it is decisive."""
    _append_search_result(bot, page, query, queries, results, query_cache)
    manual_match = manual_review_result(bot, item, started_at, queries, results)
    if manual_match:
        return manual_match
    decision = _match_decision(bot, item, results)
    match = decision.best_match
    if not match:
        decisive_match(bot, item, decision, started_at, queries, require_available)
        return None
    is_final = decisive_match(
        bot, item, decision, started_at, queries, require_available
    )
    if not is_final:
        return None
    return bot.last_match_decision.best_match if bot.last_match_decision else match


def _append_search_result(bot, page, query, queries, results, query_cache) -> None:
    """Search once per query and append the cached result to this item's history."""
    queries.append(query)
    found = cached_query_result(query_cache, query, lambda: search_products(bot, page, query))
    results.append((query, found))

def _handle_no_match(
    bot,
    item: Item,
    queries: list[str],
    results: list[tuple[str, list]],
    require_available: bool,
):
    """Record and raise a descriptive error when all search attempts fail."""
    decision = _match_decision(bot, item, results)
    decision = bot.resolve_order_ai_decision(item, decision)
    write_match_log(bot, item, decision)
    if decision.best_match:
        return accepted_no_match_result(bot, item, decision, require_available)
    flagged = aggressive_review_result(bot, item, decision, require_available)
    if flagged:
        return flagged

    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(queries)} queries."
    )


def _match_decision(bot, item: Item, results: list[tuple[str, list]]):
    """Return the best decision after applying saved manual-review filters."""
    filtered = filter_manual_review_candidates(item, results)
    return explain_best_product_match(item, filtered, bot.config.matching)
