"""Matching helpers for Tawreed API execution flows."""

from __future__ import annotations

import time
from ..core.candidate_identity import candidate_has_store_product_id
from ..core.manual_review_runtime import (
    manual_review_match,
    manual_review_queries,
    saved_manual_review_decision,
)
from ..core.product_matching import _search_queries_for_item, explain_best_product_match
from ..core.utils.excel import Item
from .tawreed_api import TawreedApiClient
from .tawreed_match_logs import write_match_log
from .tawreed_query_cache import cached_query_result, get_bot_query_cache
from .tawreed_search_decision import decisive_match
from .tawreed_timing import record_timing


def require_api_match(bot, api: TawreedApiClient, item: Item, require_available: bool):
    """Return an accepted API match for one order item or raise a skip exception."""
    started_at = time.perf_counter()
    queries, results = [], []
    query_cache = get_bot_query_cache(bot)
    review_decision = _manual_review_decision_timed(bot, item)
    
    for query in manual_review_queries(item, _search_queries_for_item(item), review_decision):
        queries.append(query)
        found = cached_query_result(query_cache, query, lambda: _search_products_timed(bot, api, query))
        results.append((query, found))
        match = _check_api_match(bot, item, started_at, queries, results, require_available, review_decision)
        if match:
            return match
    
    return _handle_api_no_match(bot, item, queries, results, require_available, review_decision)


def _check_api_match(
    bot, item, started_at, queries, results, require_available, review_decision
) -> Any | None:
    """Helper to check manual or automated api match."""
    decision = _api_match_decision(bot, item, results, review_decision)
    if _is_saved_manual_review_match(decision):
        bot.last_match_decision, bot.last_searched_queries = decision, queries
        bot.last_match_elapsed_seconds = time.perf_counter() - started_at
        return decision.best_match
    if decisive_match(bot, item, decision, started_at, queries, require_available):
        return bot.last_match_decision.best_match
    return None


def _search_products_timed(bot, api: TawreedApiClient, query: str):
    """Search through the API and accumulate live network timing."""
    started_at = time.perf_counter()
    try:
        return api.search_products(query)
    finally:
        record_timing(bot, "api_search_seconds", time.perf_counter() - started_at)


def _manual_review_decision_timed(bot, item: Item):
    """Return one saved manual-review decision and record lookup/cache time."""
    started_at = time.perf_counter()
    try:
        return saved_manual_review_decision(item)
    finally:
        record_timing(
            bot, "manual_review_lookup_seconds", time.perf_counter() - started_at
        )


def _api_match_decision(bot, item: Item, results, review_decision=None):
    """Return the API match decision and accumulate decision CPU/storage timing."""
    started_at = time.perf_counter()
    try:
        manual = manual_review_match(item, results, review_decision)
        if manual:
            return manual
        return explain_best_product_match(item, results, bot.config.matching)
    finally:
        record_timing(
            bot, "match_decision_seconds", time.perf_counter() - started_at
        )


def _handle_api_no_match(
    bot, item: Item, queries: list[str], results,
    require_available: bool, review_decision=None
):
    if _has_only_non_orderable_candidates(results):
        _raise_non_orderable_exception(bot, item, results)

    decision = _api_match_decision(bot, item, results, review_decision)
    decision = bot.resolve_order_ai_decision(item, decision)
    write_match_log(bot, item, decision)
    if decision.best_match:
        return _accepted_api_match(bot, item, decision, require_available)
    raise bot.no_results_exception(
        f"No decisive match found for '{item.name}' after {len(queries)} queries."
    )


def _raise_non_orderable_exception(bot, item, results):
    """Raise exception for non-orderable candidates."""
    from ..core.matching_models import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown

    candidates = [(q, c) for q, rows in results for c in rows]
    diagnostics = []
    if candidates:
        query, candidate = candidates[0]
        diagnostics.append(CandidateMatchDiagnostic(
            query=query, row_index=0, score=999.0, sort_key=(999.0, 0, 0.0, 0, 0, 0),
            accepted=False, accepted_reason="", rejection_reason="Candidate missing orderable storeProductId",
            breakdown=MatchScoreBreakdown(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 999.0), candidate=candidate
        ))
    
    bot.last_match_decision = MatchDecision(best_match=None, diagnostics=diagnostics, final_reason="All API candidates missing orderable storeProductId")
    raise bot.no_results_exception(f"No decisive match found for '{item.name}'. API candidates found but none has an orderable storeProductId.")



def _has_only_non_orderable_candidates(results) -> bool:
    """Return whether API search found rows but none can be ordered."""
    candidates = [candidate for _query, rows in results for candidate in rows]
    return bool(candidates) and not any(
        candidate_has_store_product_id(candidate) for candidate in candidates
    )


def _accepted_api_match(bot, item: Item, decision, require_available: bool):
    match = decision.best_match
    if require_available and int(match.data.get("availableQuantity") or 0) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
    return match


def _is_saved_manual_review_match(decision) -> bool:
    return bool(
        decision.best_match
        and str(decision.final_reason).startswith("Approved by saved manual review")
    )
