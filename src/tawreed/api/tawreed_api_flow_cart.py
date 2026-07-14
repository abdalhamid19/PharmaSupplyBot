"""Cart operations for Tawreed API flow."""

from __future__ import annotations

import time
from typing import Iterable

from src.core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient


def _add_api_order_items(bot, api: TawreedApiClient, items: Iterable[Item]) -> bool:
    """Add every requested item through the API and record summaries."""
    from ..matching.tawreed_timing import record_timing
    
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
    from .tawreed_api_flow_matching import require_api_match
    from ..store.tawreed_store_summary import record_single_store
    
    match = require_api_match(bot, api, item, True)
    has_product_id = bool(match.data.get("productId") or match.data.get("id"))
    is_multi = int(match.data.get("productsCount") or 0) > 0 and has_product_id
    if is_multi:
        from .tawreed_api_flow_multistore import _add_multi_store_item_api
        _add_multi_store_item_api(bot, api, match, item, record_timing)
    else:
        _add_single_item_to_cart(bot, api, match, item, record_timing)
        record_single_store(bot, match.data)


def _add_single_item_to_cart(bot, api, match, item, record_timing):
    """Execute add-to-cart API call and record timing."""
    from src.core.matching.candidate_identity import candidate_has_store_product_id
    from ..products.tawreed_products_flow import _min_disc
    from ..store.tawreed_pricing import discount_value_as_percent, first_discount_value

    if not candidate_has_store_product_id(match.data):
        raise bot.skip_item_exception(
            f"Matched product is not orderable (missing storeProductId) "
            f"for '{item.name}'."
        )

    min_discount = _min_disc(bot)
    if min_discount > 0:
        store_discount = discount_value_as_percent(first_discount_value(match.data))
        if store_discount < min_discount - 0.001:
            raise bot.skip_item_exception(
                f"Store discount ({store_discount:g}%) is below minimum ({min_discount:g}%)."
            )

    cart_start = time.perf_counter()
    try:
        api.add_to_cart(match, int(item.qty))
    except ValueError as error:
        # Defense in depth: never let empty/invalid storeProductId crash the run.
        message = str(error)
        if "storeProductId" in message:
            raise bot.skip_item_exception(message) from error
        raise
    record_timing(bot, "add_to_cart_seconds", time.perf_counter() - cart_start)
    bot.last_ordered_total_qty = int(item.qty)


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


__all__ = [
    "_add_api_order_items",
    "_add_single_api_item",
    "_add_single_item_to_cart",
    "_submit_order_if_enabled",
]
