"""Tawreed flow helpers for saved manual-review matches."""

from __future__ import annotations

import time

from ..core.manual_review_runtime import manual_review_match
from .tawreed_match_logs import write_match_log


def accepted_manual_review_match(bot, item, decision, started_at, queries):
    """Record and return a saved human-approved match from current candidates."""
    bot.last_match_decision, bot.last_searched_queries = decision, queries
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    write_match_log(bot, item, decision)
    return decision.best_match


def manual_review_result(bot, item, started_at, queries, results):
    """Return a saved manual-review match from current candidates when available."""
    decision = manual_review_match(item, results)
    if not decision:
        return None
    return accepted_manual_review_match(bot, item, decision, started_at, queries)
