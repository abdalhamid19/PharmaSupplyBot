"""Add-to-cart API functions for Tawreed."""

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api import TawreedApiClient
from .tawreed_api_matching import require_api_match
from .tawreed_api_flow_multi_store import _add_multi_store_item_api
from .tawreed_api_flow_utils import _submit_order_if_enabled, _require_contract, _warm_up_api_client


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
    from .tawreed_api_flow_multi_store import _add_multi_store_item_api
    
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
