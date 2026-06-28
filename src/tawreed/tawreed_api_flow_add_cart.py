"""Add-to-cart API functions for Tawreed (deprecated - functionality moved to tawreed_api_flow.py)."""

import time
from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api_client import TawreedApiClient
from .tawreed_api_flow import require_api_match, _add_multi_store_item_api, _submit_order_if_enabled, _require_contract, _warm_up_api_client


def place_order_with_api(bot, items: Iterable[Item]) -> None:
    """Add items to Tawreed cart through discovered API endpoints (deprecated)."""
    from .tawreed_api_flow import place_order_with_api as _place_order_with_api
    _place_order_with_api(bot, items)


def _add_api_order_items(bot, api: TawreedApiClient, items: Iterable[Item]) -> bool:
    """Add every requested item through the API and record summaries (deprecated)."""
    from .tawreed_api_flow import _add_api_order_items as _add_api_order_items_impl
    return _add_api_order_items_impl(bot, api, items)


def _add_single_api_item(bot, api, item, record_timing):
    """Add a single item via API (deprecated)."""
    from .tawreed_api_flow import _add_single_api_item as _add_single_api_item_impl
    _add_single_api_item_impl(bot, api, item, record_timing)


def _add_single_item_to_cart(bot, api, match, item, record_timing):
    """Execute add-to-cart API call and record timing (deprecated)."""
    from .tawreed_api_flow import _add_single_item_to_cart as _add_single_item_to_cart_impl
    _add_single_item_to_cart_impl(bot, api, match, item, record_timing)
