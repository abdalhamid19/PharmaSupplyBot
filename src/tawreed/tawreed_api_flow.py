"""API-backed Tawreed execution flows with browser-compatible summaries - re-exports from split modules."""

from __future__ import annotations

# Re-export from split modules
from .tawreed_api_flow_main import (
    match_items_only_with_api,
    place_order_with_api,
    remove_cart_items_with_api,
    _require_contract,
    _warm_up_api_client,
)
from .tawreed_api_flow_cart import (
    _add_api_order_items,
    _add_single_api_item,
    _add_single_item_to_cart,
    _submit_order_if_enabled,
)
from .tawreed_api_flow_multistore import (
    _add_multi_store_item_api,
    _validate_max_discount_if_needed,
    _select_stores_and_add_to_cart,
    _add_store_to_cart,
    _should_stop_in_max_discount_mode,
    _finalize_multi_store_order,
)
from .tawreed_api_flow_matching import (
    require_api_match,
    _check_api_match,
    _search_products_timed,
    _manual_review_decision_timed,
    _api_match_decision,
    _handle_api_no_match,
    _raise_non_orderable_exception,
    _has_only_non_orderable_candidates,
    _accepted_api_match,
    _is_saved_manual_review_match,
)


__all__ = [
    # Re-exports from main
    "match_items_only_with_api",
    "place_order_with_api",
    "remove_cart_items_with_api",
    "_require_contract",
    "_warm_up_api_client",
    # Re-exports from cart
    "_add_api_order_items",
    "_add_single_api_item",
    "_add_single_item_to_cart",
    "_submit_order_if_enabled",
    # Re-exports from multistore
    "_add_multi_store_item_api",
    "_validate_max_discount_if_needed",
    "_select_stores_and_add_to_cart",
    "_add_store_to_cart",
    "_should_stop_in_max_discount_mode",
    "_finalize_multi_store_order",
    # Re-exports from matching
    "require_api_match",
    "_check_api_match",
    "_search_products_timed",
    "_manual_review_decision_timed",
    "_api_match_decision",
    "_handle_api_no_match",
    "_raise_non_orderable_exception",
    "_has_only_non_orderable_candidates",
    "_accepted_api_match",
    "_is_saved_manual_review_match",
]
