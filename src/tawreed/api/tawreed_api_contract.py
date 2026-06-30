"""Tawreed API endpoint contract persistence, discovery, and defaults.

Re-exports from split modules.
"""

from __future__ import annotations

# Re-export from split modules
from .tawreed_api_contract_base import (
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
)
from .tawreed_api_contract_discovery import (
    begin_api_contract_capture,
    save_api_contract_capture,
    begin_detailed_api_capture,
    save_captured_requests,
    analyze_add_to_cart_payload,
)


__all__ = [
    # Re-exports from base
    "DEFAULT_CONTRACT_PATH",
    "TawreedApiContract",
    "TawreedApiUnavailable",
    "load_api_contract",
    "save_discovered_api_contract",
    "save_contract_requests",
    "contract_type",
    "DEFAULT_PRODUCT_SEARCH_URL",
    "DEFAULT_PRODUCT_SEARCH_BODY",
    "product_search_url",
    "product_search_body",
    # Re-exports from discovery
    "begin_api_contract_capture",
    "save_api_contract_capture",
    "begin_detailed_api_capture",
    "save_captured_requests",
    "analyze_add_to_cart_payload",
]
