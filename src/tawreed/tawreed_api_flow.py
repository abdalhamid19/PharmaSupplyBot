"""API-backed Tawreed execution flows with browser-compatible summaries."""

from __future__ import annotations

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api import TawreedApiClient
from .tawreed_api_matching import require_api_match


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
                
                bot._record_match_only_success(item, started_at)
            except bot.skip_item_exception as error:
                bot._record_match_only_skip(item, error, started_at)


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
    from .tawreed_store_summary import record_single_store
    
    added_any = False
    for item in items:
        if bot._stop_before_item(item):
            return added_any
        started_at = time.perf_counter()
        bot._reset_last_item_state()
        try:
            match = require_api_match(bot, api, item, True)
            has_product_id = bool(match.data.get("productId") or match.data.get("id"))
            is_multi = int(match.data.get("productsCount") or 0) > 0 and has_product_id
            if is_multi:
                _add_multi_store_item_api(bot, api, match, item, record_timing)
            else:
                _add_single_item_to_cart(bot, api, match, item, record_timing)
                record_single_store(bot, match.data)
            bot._record_success(item, started_at)
            added_any = True
        except bot.skip_item_exception as error:
            bot._record_skip(item, error, started_at)
    return added_any


def _add_multi_store_item_api(bot, api: TawreedApiClient, match, item: Item, record_timing) -> None:
    """Order from multiple stores natively using the API payload."""
    from .tawreed_store_selection import choose_next_store_for_remaining_quantity
    from .tawreed_products_flow import _wh_mode, _effective_min_discount, _record_stores, _find_max_discount, _min_disc

    store_rows = api.get_store_details(match.data.get("productId") or match.data.get("id"))
    if not store_rows:
        raise bot.skip_item_exception("API multi-store returned no stores.")

    rem, used_ids, sels = int(item.qty), set(), []
    mode = _wh_mode(bot)
    
    # In max_discount mode, find the highest discount first
    max_discount_value = None
    if mode == "max_discount" and store_rows:
        max_discount_value = _find_max_discount(store_rows)
        # Check if highest discount meets minimum requirement
        min_discount = _min_disc(bot)
        if max_discount_value < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Highest discount ({max_discount_value:g}%) is below minimum ({min_discount:g}%)."
            )
    
    while rem > 0:
        min_disc = _effective_min_discount(bot, sels)
        choice = choose_next_store_for_remaining_quantity(
            store_rows, used_ids, mode, bot.skip_item_exception, min_disc
        )
        if choice is None:
            break
            
        ordered = min(rem, choice.available_quantity)
        if ordered <= 0:
            break

        cart_start = time.perf_counter()
        api.add_to_cart(choice.store, ordered)
        record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)

        sels.append((choice.store, ordered))
        used_ids.add(choice.identity)
        rem -= ordered
        
        # In max_discount mode, only use stores within 0.5% of max discount
        if mode == "max_discount" and max_discount_value is not None:
            if choice.discount_percent < max_discount_value - 0.5:
                break

    if not sels:
        raise bot.skip_item_exception("All stores out of stock.")
    bot.last_ordered_total_qty = sum(q for _, q in sels)
    _record_stores(bot, sels)


def _add_single_item_to_cart(bot, api, match, item, record_timing):
    """Execute add-to-cart API call and record timing."""
    from .tawreed_products_flow import _min_disc
    from .tawreed_pricing import discount_value_as_percent, first_discount_value
    
    # Check min_discount_percent for single-store products
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
    from .tawreed_api import TawreedApiUnavailable

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
