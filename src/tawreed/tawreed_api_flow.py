"""API-backed Tawreed execution flows with browser-compatible summaries."""

from __future__ import annotations

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient
from .tawreed_api_contract import TawreedApiUnavailable


# ============================================================================
# Main API Flow
# ============================================================================

def match_items_only_with_api(bot, items: Iterable[Item]) -> None:
    """Match items through Tawreed API without opening Chromium."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url")
        _warm_up_api_client(bot, api)
        for item in items:
            if bot._stop_before_item(item):
                return
            started_at = time.perf_counter()
            bot._reset_last_item_state()
            try:
                match = require_api_match(bot, api, item, False)
                bot.log(f"API match-only accepted {item.code} / {item.name}: {match.query}")
                
                from .tawreed_store_summary import record_single_store
                record_single_store(bot, getattr(match, "data", {}))
                
                bot.order_flow.summary_recorder.record_match_only_success(item, started_at)
            except bot.skip_item_exception as error:
                bot.order_flow.summary_recorder.record_match_only_skip(item, error, started_at)


# ============================================================================
# Add-to-Cart Flow
# ============================================================================

def place_order_with_api(bot, items: Iterable[Item]) -> None:
    """Add items to Tawreed cart through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "product_search_url", "add_to_cart_url")
        if bot.config.runtime.submit_order:
            _require_contract(api, "submit_order_url")
        _warm_up_api_client(bot, api)
        added_any = _add_api_order_items(bot, api, items)
        _submit_order_if_enabled(bot, api, added_any)


def _add_api_order_items(bot, api: TawreedApiClient, items: Iterable[Item]) -> bool:
    """Add every requested item through the API and record summaries."""
    from .tawreed_timing import record_timing
    
    added_any = False
    for item in items:
        if bot._stop_before_item(item):
            return added_any
        started_at = time.perf_counter()
        bot._reset_last_item_state()
        try:
            _add_single_api_item(bot, api, item, record_timing)
            bot.order_flow.summary_recorder.record_success(item, started_at)
            added_any = True
        except bot.skip_item_exception as error:
            bot.order_flow.summary_recorder.record_skip(item, error, started_at)
    return added_any


def _add_single_api_item(bot, api, item, record_timing):
    """Add a single item via API."""
    from .tawreed_store_summary import record_single_store
    
    match = require_api_match(bot, api, item, True)
    has_product_id = bool(match.data.get("productId") or match.data.get("id"))
    is_multi = int(match.data.get("productsCount") or 0) > 0 and has_product_id
    if is_multi:
        _add_multi_store_item_api(bot, api, match, item, record_timing)
    else:
        _add_single_item_to_cart(bot, api, match, item, record_timing)
        record_single_store(bot, match.data)


def _add_single_item_to_cart(bot, api, match, item, record_timing):
    """Execute add-to-cart API call and record timing."""
    from .tawreed_products_flow import _min_disc
    from .tawreed_pricing import discount_value_as_percent, first_discount_value
    
    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )
    
    cart_start = time.perf_counter()
    api.add_to_cart(match, int(item.qty))
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)
    bot.last_ordered_total_qty = int(item.qty)


# ============================================================================
# Multi-Store Flow
# ============================================================================

def _add_multi_store_item_api(bot, api: TawreedApiClient, match, item: Item, record_timing) -> None:
    """Order from multiple stores natively using the API payload."""
    from .tawreed_store_selection import choose_next_store_for_remaining_quantity
    from .tawreed_products_flow_discount import _wh_mode, _min_disc, _preferred_warehouses
    
    store_rows = api.get_store_details(match.data.get("productId") or match.data.get("id"))
    if not store_rows:
        raise bot.skip_item_exception("API multi-store returned no stores.")
    
    mode = _wh_mode(bot)
    max_discount_value = _validate_max_discount_if_needed(bot, mode, store_rows)
    
    sels = _select_stores_and_add_to_cart(
        bot, api, item, store_rows, mode, max_discount_value, 
        _preferred_warehouses(bot), record_timing
    )
    
    _finalize_multi_store_order(bot, sels)


def _validate_max_discount_if_needed(bot, mode, store_rows):
    """Validate max discount meets minimum requirement if in max_discount mode."""
    from .tawreed_products_flow_discount import _find_max_discount, _min_disc
    
    if mode != "max_discount" or not store_rows:
        return None
    
    max_discount_value = _find_max_discount(store_rows)
    min_discount = _min_disc(bot)
    if max_discount_value < min_discount - 0.001:
        raise bot.skip_item_exception(
            f"Highest discount ({max_discount_value:g}%) is below minimum ({min_discount:g}%)."
        )
    return max_discount_value


def _select_stores_and_add_to_cart(
    bot, api, item, store_rows, mode, max_discount_value,
    preferred_warehouses, record_timing
):
    """Select stores and add items to cart until quantity is fulfilled."""
    from .tawreed_store_selection import choose_next_store_for_remaining_quantity
    from .tawreed_products_flow_discount import _effective_min_discount
    
    rem, used_ids, sels = int(item.qty), set(), []
    while rem > 0:
        choice = choose_next_store_for_remaining_quantity(
            store_rows, used_ids, mode, bot.skip_item_exception,
            _effective_min_discount(bot, sels), preferred_warehouses
        )
        if not choice or min(rem, choice.available_quantity) <= 0:
            break
        ordered = min(rem, choice.available_quantity)
        _add_store_to_cart(api, choice, ordered, bot, record_timing)
        sels.append((choice.store, ordered))
        used_ids.add(choice.identity)
        rem -= ordered
        if _should_stop_in_max_discount_mode(mode, max_discount_value, choice):
            break
    return sels


def _add_store_to_cart(api, choice, ordered, bot, record_timing):
    """Add a single store to cart and record timing."""
    cart_start = time.perf_counter()
    api.add_to_cart(choice.store, ordered)
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)


def _should_stop_in_max_discount_mode(mode, max_discount_value, choice):
    """Check if we should stop adding more stores in max_discount mode."""
    if mode == "max_discount" and max_discount_value is not None:
        if choice.discount_percent < max_discount_value - 0.5:
            return True
    return False


def _finalize_multi_store_order(bot, sels):
    """Finalize multi-store order and record stores."""
    from .tawreed_products_flow_stores import _record_stores
    
    if not sels:
        raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)


# ============================================================================
# Flow Utilities
# ============================================================================

def remove_cart_items_with_api(bot, items: Iterable[object]) -> None:
    """Remove requested cart items through discovered API endpoints."""
    with TawreedApiClient(bot.config.base_url, bot.state_path) as api:
        _require_contract(api, "remove_cart_url")
        _warm_up_api_client(bot, api)
        for item in items:
            if bot._stop_requested():
                return
            api.remove_cart_item(item)


def _submit_order_if_enabled(bot, api: TawreedApiClient, added_any: bool) -> None:
    if not added_any or bot._stop_requested():
        print(f"[{bot.profile_key}] Stop requested or incomplete. Order confirmation skipped.")
        return
    if getattr(bot, "match_only", False):
        print(f"[{bot.profile_key}] Match-only run. Final order submission skipped.")
        return
    if not bot.config.runtime.submit_order:
        print(f"[{bot.profile_key}] Items added to cart. Final order submission is disabled.")
        return
    api.submit_order()


def _require_contract(api: TawreedApiClient, *fields: str) -> None:
    """Raise before item iteration when the discovered contract is incomplete."""
    missing = [field for field in fields if not api.contract_field_available(field)]
    if missing:
        raise TawreedApiUnavailable(f"Missing Tawreed API contract fields: {missing}")


def _warm_up_api_client(bot, api: TawreedApiClient) -> None:
    """Open the API request context once before per-item timing starts."""
    started_at = time.perf_counter()
    api.warm_up()
    elapsed = time.perf_counter() - started_at
    if hasattr(bot, "_record_pending_item_timing"):
        bot._record_pending_item_timing("api_context_init_seconds", elapsed)


# ============================================================================
# API Matching
# ============================================================================

def require_api_match(bot, api: TawreedApiClient, item: Item, require_available: bool):
    """Return an accepted API match for one order item or raise a skip exception."""
    from ..core.candidate_identity import candidate_has_store_product_id
    from ..core.manual_review_runtime import (
        manual_review_match,
        manual_review_queries,
        saved_manual_review_decision,
    )
    from ..core.product_matching import _search_queries_for_item, explain_best_product_match
    from .tawreed_match_logs import write_match_log
    from .tawreed_query_cache import cached_query_result, get_bot_query_cache
    from .tawreed_search_decision import decisive_match
    from .tawreed_timing import record_timing
    
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
    from ..core.manual_review_runtime import saved_manual_review_decision
    from ..core.product_matching import explain_best_product_match
    from .tawreed_search_decision import decisive_match
    from .tawreed_timing import record_timing
    
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
    from .tawreed_timing import record_timing
    
    started_at = time.perf_counter()
    try:
        return api.search_products(query)
    finally:
        record_timing(bot, "api_search_seconds", time.perf_counter() - started_at)


def _manual_review_decision_timed(bot, item: Item):
    """Return one saved manual-review decision and record lookup/cache time."""
    from ..core.manual_review_runtime import saved_manual_review_decision
    from .tawreed_timing import record_timing
    
    started_at = time.perf_counter()
    try:
        return saved_manual_review_decision(item)
    finally:
        record_timing(
            bot, "manual_review_lookup_seconds", time.perf_counter() - started_at
        )


def _api_match_decision(bot, item: Item, results, review_decision=None):
    """Return the API match decision and accumulate decision CPU/storage timing."""
    from ..core.manual_review_runtime import manual_review_match
    from ..core.product_matching import explain_best_product_match
    from .tawreed_timing import record_timing
    
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
    from ..core.candidate_identity import candidate_has_store_product_id
    from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown
    from .tawreed_match_logs import write_match_log
    
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
    from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown

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
    from ..core.candidate_identity import candidate_has_store_product_id
    
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


__all__ = [
    "TawreedApiClient",
    "match_items_only_with_api",
    "place_order_with_api",
    "remove_cart_items_with_api",
    "_add_api_order_items",
    "_add_single_api_item",
    "_add_single_item_to_cart",
    "_add_multi_store_item_api",
    "_validate_max_discount_if_needed",
    "_select_stores_and_add_to_cart",
    "_add_store_to_cart",
    "_should_stop_in_max_discount_mode",
    "_finalize_multi_store_order",
    "_submit_order_if_enabled",
    "_require_contract",
    "_warm_up_api_client",
    "require_api_match",
]
