"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..core.manual_review_runtime import (
    filter_manual_review_candidates,
    manual_review_match,
    manual_review_queries,
    saved_manual_review_decision,
)
from ..core.matching_types import SearchMatch
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_aggressive_matching import aggressive_review_result, available_quantity
from .tawreed_match_logs import write_match_log
from .tawreed_query_cache import cached_query_result, get_bot_query_cache
from .tawreed_search_decision import decisive_match
from .tawreed_timing import record_timing


def require_product_match(bot, page: Page, item: Item, require_available: bool = True) -> tuple[SearchMatch, str]:
    """Search Tawreed query variants until a decisive match is found."""
    queries, results = [], []
    cache = get_bot_query_cache(bot)
    started_at = time.perf_counter()
    review_decision = _manual_review_decision_timed(bot, item)
    
    for q in manual_review_queries(item, _search_queries_for_item(item), review_decision):
        match = _search_one_query(bot, page, item, q, started_at, queries, results, cache, require_available, review_decision)
        if match:
            return match, q
    
    return _handle_no_match(bot, item, queries, results, require_available, review_decision)


def _search_one_query(bot, page, item, query, started_at, queries, results, query_cache, require_available, review_decision):
    """Search one query and return the final match when it is decisive."""
    _append_search_result(bot, page, query, queries, results, query_cache)
    manual_match = manual_review_result(bot, item, started_at, queries, results, review_decision)
    if manual_match:
        return manual_match
    
    decision = _match_decision(bot, item, results, review_decision)
    match = decision.best_match
    if not match:
        decisive_match(bot, item, decision, started_at, queries, require_available)
        return None
    
    is_final = decisive_match(bot, item, decision, started_at, queries, require_available)
    return bot.last_match_decision.best_match if is_final else None


def _append_search_result(bot, page, query, queries, results, query_cache) -> None:
    """Search once per query and append the cached result to this item's history."""
    from .products.tawreed_product_search import search_products

    queries.append(query)
    found = cached_query_result(query_cache, query, lambda: search_products(bot, page, query))
    results.append((query, found))


def _handle_no_match(bot, item, queries, results, require_available, review_decision):
    """Record and raise a descriptive error when all search attempts fail."""
    decision = bot.resolve_order_ai_decision(
        item, _match_decision(bot, item, results, review_decision)
    )
    write_match_log(bot, item, decision)
    if decision.best_match:
        return accepted_no_match_result(bot, item, decision, require_available)
    flagged = aggressive_review_result(bot, item, decision, require_available)
    if flagged:
        return flagged
    msg = f"No decisive match found for '{item.name}' after {len(queries)} queries."
    raise bot.no_results_exception(msg)


def _manual_review_decision_timed(bot, item: Item):
    """Return one saved manual-review decision and record lookup/cache time."""
    started_at = time.perf_counter()
    try:
        return saved_manual_review_decision(item)
    finally:
        record_timing(
            bot, "manual_review_lookup_seconds", time.perf_counter() - started_at
        )


def _match_decision(bot, item: Item, results: list[tuple[str, list]], review_decision=None):
    """Return the best decision after applying saved manual-review filters."""
    started_at = time.perf_counter()
    forced_match = manual_review_match(item, results, review_decision)
    try:
        if forced_match:
            return forced_match
        filtered = filter_manual_review_candidates(item, results, review_decision)
        return explain_best_product_match(item, filtered, bot.config.matching)
    finally:
        record_timing(
            bot, "match_decision_seconds", time.perf_counter() - started_at
        )


# ============================================================================
# Match acceptance helpers (from tawreed_match_acceptance.py)
# ============================================================================

def accepted_no_match_result(bot, item: Item, decision, require_available: bool):
    """Return an AI-selected match from the no-match path after stock checks."""
    match = decision.best_match
    if require_available and available_quantity(match.data) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
    return match, match.query


# ============================================================================
# Manual review flow helpers (from tawreed_manual_review_flow.py)
# ============================================================================

def manual_review_result(bot, item, started_at, queries, results, review_decision=None):
    """Return a saved manual-review match from current candidates when available."""
    decision = manual_review_match(item, results, review_decision)
    if not decision:
        return None
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    return decision.best_match


__all__ = [
    "require_product_match",
    "accepted_no_match_result",
    "manual_review_result",
]
