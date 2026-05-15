"""Default read-only Tawreed API contract values."""

from __future__ import annotations

from typing import Any

from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT

DEFAULT_PRODUCT_SEARCH_URL = (
    f"/rest/v2/{PRODUCT_SEARCH_ENDPOINT}?sort=productName,asc&page=0&size=50"
)
DEFAULT_PRODUCT_SEARCH_BODY = {
    "mode": "error",
    "langCode": "ar",
    "data": {"displayType": 1},
}


def product_search_url(contract) -> str:
    """Return a discovered or safe default product-search endpoint."""
    return str(getattr(contract, "product_search_url", "") or DEFAULT_PRODUCT_SEARCH_URL)


def product_search_body(contract) -> dict[str, Any]:
    """Return a discovered or safe default product-search body."""
    return getattr(contract, "product_search_body", None) or DEFAULT_PRODUCT_SEARCH_BODY
