"""Default read-only Tawreed API contract values (deprecated - functionality moved to tawreed_api_contract.py)."""

from __future__ import annotations

from typing import Any

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

# This file is now deprecated - functionality moved to tawreed_api_contract.py
# Keeping for backward compatibility

DEFAULT_PRODUCT_SEARCH_URL = (
    f"/rest/v2/{PRODUCT_SEARCH_ENDPOINT}?sort=productName,asc&page=0&size=50"
)
DEFAULT_PRODUCT_SEARCH_BODY = {
    "mode": "error",
    "langCode": "ar",
    "data": {"displayType": 1},
}


def product_search_url(contract) -> str:
    """Return a discovered or safe default product-search endpoint (deprecated)."""
    from .tawreed_api_contract import product_search_url as _product_search_url
    return _product_search_url(contract)


def product_search_body(contract) -> dict[str, Any]:
    """Return a discovered or safe default product-search body (deprecated)."""
    from .tawreed_api_contract import product_search_body as _product_search_body
    return _product_search_body(contract)
