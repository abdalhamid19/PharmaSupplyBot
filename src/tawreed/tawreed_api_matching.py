"""Matching helpers for Tawreed API execution flows."""

from __future__ import annotations

import time

from ..core.manual_review_runtime import manual_review_match, manual_review_queries
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_api import TawreedApiClient
from .tawreed_match_logs import write_match_log
from .tawreed_search_decision import decisive_match


def require_api_match(bot, api: TawreedApiClient, item: Item, require_available: bool):
    """Return an accepted API match for one order item or raise a skip exception."""
    started_at = time.perf_counter()
    queries: list[str] = []
    results = []
    for query in manual_review_queries(item, _search_queries_for_item(item)):
        queries.append(query)
        results.append((query, api.search_products(query)))
        manual_decision = manual_review_match(item, results)
        if manual_decision:
            bot.last_match_decision, bot.last_searched_queries = manual_decision, queries
            return manual_decision.best_match
        decision = explain_best_product_match(item, results, bot.config.matching)
        if decisive_match(bot, item, decision, started_at, queries, require_available):
            return bot.last_match_decision.best_match
    return _handle_api_no_match(bot, item, queries, results, require_available)


def _handle_api_no_match(bot, item: Item, queries: list[str], results, require_available: bool):
    decision = explain_best_product_match(item, results, bot.config.matching)
    decision = bot.resolve_order_ai_decision(item, decision)
    write_match_log(bot, item, decision)
    if decision.best_match:
        return _accepted_api_match(bot, item, decision, require_available)
    raise bot.no_results_exception(
        f"No decisive API match found for '{item.name}' after {len(queries)} queries."
    )


def _accepted_api_match(bot, item: Item, decision, require_available: bool):
    match = decision.best_match
    if require_available and int(match.data.get("availableQuantity") or 0) <= 0:
        raise bot.skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
    return match
