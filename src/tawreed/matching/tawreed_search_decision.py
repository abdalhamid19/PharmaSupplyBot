"""Final-match decision helpers for Tawreed product searches."""

from __future__ import annotations

import time

from src.core.matching.matching_confidence import match_confidence
from src.core.matching_types import MatchDecision
from src.core.matching.product_matching import is_decisive_product_match
from src.core.utils.excel import Item
from .tawreed_match_logs import write_match_log
from .tawreed_aggressive_matching import available_quantity

MIN_SEARCH_QUERIES_PER_ITEM = 3


def decisive_match(
    bot,
    item: Item,
    decision: MatchDecision,
    started_at: float,
    queries: list[str],
    require_available: bool = True,
) -> bool:
    """Return whether the current decision is final and record the outcome."""
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    if not decision.best_match:
        _write_pending_match_log(bot, item, decision, queries)
        return False
    if not _is_final_match(bot, item, decision, queries):
        return False
    _record_final_match(bot, item, decision, started_at, require_available)
    return True


def _is_final_match(
    bot, item: Item, decision: MatchDecision, queries: list[str]
) -> bool:
    """Return whether the current best match can finish the query loop."""
    match = decision.best_match
    if not match or getattr(bot, "fast_search", False):
        return bool(match)
    is_decisive = is_decisive_product_match(queries[-1], match.data)
    if is_decisive:
        return True
    matching = bot.config.matching
    confidence = match_confidence(decision, item, queries[-1])
    if confidence >= matching.early_stop_confidence:
        return True
    return len(queries) >= MIN_SEARCH_QUERIES_PER_ITEM


def _write_pending_match_log(
    bot, item: Item, decision: MatchDecision, queries: list[str]
) -> None:
    """Write match logs once enough query attempts have been tried."""
    if len(queries) >= MIN_SEARCH_QUERIES_PER_ITEM:
        write_match_log(bot, item, decision)


def _record_final_match(
    bot,
    item: Item,
    decision: MatchDecision,
    started_at: float,
    require_available: bool,
) -> None:
    """Record final match timing/logs and optionally reject unavailable matches."""
    decision = bot.resolve_order_ai_decision(item, decision)
    if not decision.best_match:
        raise bot.skip_item_exception("AI matching requires manual review.")
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    if require_available and _available_quantity(decision) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )


def _available_quantity(decision: MatchDecision) -> int:
    """Return the matched product availability as an integer quantity."""
    return available_quantity(decision.best_match.data if decision.best_match else {})
