"""Search and product matching logic for Tawreed flows."""

from __future__ import annotations

import time
from typing import Any

from playwright.sync_api import Page

from ..core.manual_review_runtime import manual_review_match, manual_review_queries
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

    for query in manual_review_queries(item, _search_queries_for_item(item)):
        match = _search_one_query(
            bot, page, item, query, started_at, queries, results, require_available
        )
        if match:
            return match, query

    return _handle_no_match(bot, item, queries, results, require_available)


def _search_one_query(
    bot, page, item, query, started_at, queries, results, require_available
):
    """Search one query and return the final match when it is decisive."""
    queries.append(query)
    results.append((query, search_products(bot, page, query)))
    manual_decision = manual_review_match(item, results)
    if manual_decision:
        return _accepted_manual_review_match(bot, item, manual_decision, started_at, queries)
    decision = explain_best_product_match(item, results, bot.config.matching)
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


def _accepted_manual_review_match(bot, item, decision, started_at, queries):
    """Record and return a saved human-approved match from current candidates."""
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    return decision.best_match


def _handle_no_match(
    bot,
    item: Item,
    queries: list[str],
    results: list[tuple[str, list]],
    require_available: bool,
):
    """Record and raise a descriptive error when all search attempts fail."""
    decision = explain_best_product_match(item, results, bot.config.matching)
    decision = bot.resolve_order_ai_decision(item, decision)
    write_match_log(bot, item, decision)
    if decision.best_match:
        return _accepted_no_match_result(bot, item, decision, require_available)

    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(queries)} queries."
    )

def _accepted_no_match_result(bot, item: Item, decision, require_available: bool):
    """Return an AI-selected match from the no-match path after stock checks."""
    match = decision.best_match
    if require_available and _available_quantity(match.data) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
    return match, match.query


def _available_quantity(candidate: dict[str, Any]) -> int:
    """Return available quantity from a Tawreed candidate."""
    try:
        return int(candidate.get("availableQuantity") or 0)
    except (TypeError, ValueError):
        return 0
