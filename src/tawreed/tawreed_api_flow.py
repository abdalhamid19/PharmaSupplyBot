"""API-backed Tawreed execution flows with browser-compatible summaries."""

from __future__ import annotations

from typing import Iterable

from ..core.utils.excel import Item
from .tawreed_api_flow_main import match_items_only_with_api
from .tawreed_api_flow_add_cart import (
    place_order_with_api,
    _add_api_order_items,
    _add_single_api_item,
    _add_single_item_to_cart,
)
from .tawreed_api_flow_multi_store import (
    _add_multi_store_item_api,
    _validate_max_discount_if_needed,
    _select_stores_and_add_to_cart,
    _add_store_to_cart,
    _should_stop_in_max_discount_mode,
    _finalize_multi_store_order,
)
from .tawreed_api_flow_utils import (
    remove_cart_items_with_api,
    _submit_order_if_enabled,
    _require_contract,
    _warm_up_api_client,
)


__all__ = [
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
]
