"""Final-match decision helpers for Tawreed product searches."""

from __future__ import annotations

import time

from ..core.matching_models import MatchDecision
from ..core.product_matching import is_decisive_product_match
from ..core.utils.excel import Item
from .tawreed_match_logs import write_match_log

MIN_SEARCH_QUERIES_PER_ITEM = 3


def decisive_match(
    bot, item: Item, decision: MatchDecision, started_at: float, queries: list[str]
) -> bool:
    """Return whether the current decision is final and record the outcome."""
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    if not decision.best_match:
        _write_pending_match_log(bot, item, decision, queries)
        return False
    if getattr(bot, "fast_search", False):
        _record_final_match(bot, item, decision, started_at)
        return True
    is_decisive = is_decisive_product_match(queries[-1], decision.best_match.data)
    if not is_decisive and len(queries) < MIN_SEARCH_QUERIES_PER_ITEM:
        return False
    _record_final_match(bot, item, decision, started_at)
    return True


def _write_pending_match_log(
    bot, item: Item, decision: MatchDecision, queries: list[str]
) -> None:
    """Write match logs once enough query attempts have been tried."""
    if len(queries) >= MIN_SEARCH_QUERIES_PER_ITEM:
        write_match_log(bot, item, decision)


def _record_final_match(
    bot, item: Item, decision: MatchDecision, started_at: float
) -> None:
    """Record final match timing/logs and reject unavailable matches."""
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    if decision.best_match.data.get("availableQuantity", 0) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
