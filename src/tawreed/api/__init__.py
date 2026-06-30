"""Tawreed API client and contract management.

This module contains all API-related functionality for Tawreed, including:
- API client with context management
- API contract discovery and persistence
- API-backed execution flows
- HTTP request helpers
- API operations and payload helpers
"""

from __future__ import annotations

# Re-export from client
from .tawreed_api_client import TawreedApiClient, TawreedApiUnavailable

# Re-export from contract
from .tawreed_api_contract import (
    DEFAULT_CONTRACT_PATH,
    TawreedApiContract,
    TawreedApiUnavailable,
    load_api_contract,
    save_discovered_api_contract,
    save_contract_requests,
    contract_type,
    DEFAULT_PRODUCT_SEARCH_URL,
    DEFAULT_PRODUCT_SEARCH_BODY,
    product_search_url,
    product_search_body,
    begin_api_contract_capture,
    save_api_contract_capture,
    begin_detailed_api_capture,
    save_captured_requests,
    analyze_add_to_cart_payload,
)

# Re-export from flow
from .tawreed_api_flow import (
    match_items_only_with_api,
    place_order_with_api,
    remove_cart_items_with_api,
)

# Re-export from operations
from .tawreed_api_operations import (
    body_with_query,
    body_with_match,
    body_with_item,
    search_products,
    get_store_details,
    add_to_cart,
    remove_cart_item,
    submit_order,
)

# Re-export from HTTP helpers
from .tawreed_api_http import (
    _api_origin,
    _is_trusted_add_to_cart_url,
    _auth_headers_from_state,
)

__all__ = [
    # Client
    "TawreedApiClient",
    "TawreedApiUnavailable",
    # Contract
    "DEFAULT_CONTRACT_PATH",
    "TawreedApiContract",
    "load_api_contract",
    "save_discovered_api_contract",
    "save_contract_requests",
    "contract_type",
    "DEFAULT_PRODUCT_SEARCH_URL",
    "DEFAULT_PRODUCT_SEARCH_BODY",
    "product_search_url",
    "product_search_body",
    "begin_api_contract_capture",
    "save_api_contract_capture",
    "begin_detailed_api_capture",
    "save_captured_requests",
    "analyze_add_to_cart_payload",
    # Flow
    "match_items_only_with_api",
    "place_order_with_api",
    "remove_cart_items_with_api",
    # Operations
    "body_with_query",
    "body_with_match",
    "body_with_item",
    "search_products",
    "get_store_details",
    "add_to_cart",
    "remove_cart_item",
    "submit_order",
    # HTTP helpers
    "_api_origin",
    "_is_trusted_add_to_cart_url",
    "_auth_headers_from_state",
]
