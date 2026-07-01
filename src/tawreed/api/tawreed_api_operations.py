"""Tawreed API operation implementations and request payload helpers."""

from __future__ import annotations

import json
from typing import Any

from src.core.matching.candidate_identity import candidate_store_product_id
from .tawreed_api_contract import product_search_body, product_search_url, TawreedApiUnavailable
from ..products.tawreed_product_search import _api_candidates
from .tawreed_api_http import _is_trusted_add_to_cart_url, _ensure_cart_item_added, _post_json


# ============================================================================
# Request Payload Helpers
# ============================================================================

def body_with_query(body: dict[str, Any], query: str) -> dict[str, Any]:
    """Return a search body with common query fields populated."""
    payload = _copy_body(body)
    data = payload.setdefault("data", {})
    if isinstance(data, dict):
        data["productName"] = query
        data.setdefault("globalSearch", query)
        data.setdefault("search", query)
    return payload


def body_with_match(body: dict[str, Any], match: Any, quantity: int) -> dict[str, Any]:
    """Return an add-to-cart body with product identity and quantity populated."""
    payload = _copy_body(body)
    candidate = match if isinstance(match, dict) else (getattr(match, "data", {}) or {})
    store_product_id = candidate_store_product_id(candidate)

    # The discovered add-to-cart request always uses mode "all" with this data
    # shape; customerId is injected by TawreedApiClient from the JWT token.
    payload["mode"] = "all"
    payload.setdefault("langCode", "ar")
    payload["data"] = {
        "customerId": None,
        "storeProductId": int(store_product_id),
        "quantity": int(quantity),
        "typeId": 1,
    }
    return payload


def body_with_item(body: dict[str, Any], item: Any) -> dict[str, Any]:
    """Return a cart-removal body with the requested item identity populated."""
    payload = _copy_body(body)
    data = payload.setdefault("data", {})
    if isinstance(data, dict):
        data["itemCode"] = getattr(item, "code", "")
        data["itemName"] = getattr(item, "name", "")
    return payload


def _copy_body(body: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(body))


# ============================================================================
# API Operations
# ============================================================================

def search_products(client, query: str) -> list[dict[str, Any]]:
    """Return product candidates from a discovered API search endpoint."""
    payload = _post_json(
        client,
        product_search_url(client.contract),
        body_with_query(product_search_body(client.contract), query),
    )
    return _api_candidates(payload)


def get_store_details(client, product_id: Any) -> list[dict[str, Any]]:
    """Fetch multiple stores for a product via API."""
    try:
        pid = int(float(str(product_id).strip()))
    except (ValueError, TypeError):
        return []

    from ..tawreed_constants import STORE_DETAILS_ENDPOINT
    from .tawreed_api_payloads import stores_from_payload
    url = f"/rest/v2/{STORE_DETAILS_ENDPOINT}?productId={pid}"
    payload = _post_json(
        client,
        url,
        {
            "mode": "error",
            "langCode": "ar",
            "data": {"productId": pid},
        },
    )
    return stores_from_payload(payload)


def add_to_cart(client, match: Any, quantity: int) -> None:
    """Add a matched product to the cart through a discovered API endpoint."""
    if not _is_trusted_add_to_cart_url(client.contract.add_to_cart_url):
        raise TawreedApiUnavailable("No trusted Tawreed add-to-cart API contract.")

    payload = body_with_match(client.contract.add_to_cart_body or {}, match, quantity)

    # Inject customer ID
    if "data" in payload and isinstance(payload["data"], dict):
        payload["data"]["customerId"] = client.customer_id

    response = _post_json(client, client.contract.add_to_cart_url, payload)
    _ensure_cart_item_added(response)


def remove_cart_item(client, item: Any) -> None:
    """Remove one cart item through a discovered API endpoint."""
    if not client.contract.remove_cart_url:
        raise TawreedApiUnavailable("No trusted Tawreed cart-removal API contract.")
    _post_json(
        client,
        client.contract.remove_cart_url,
        body_with_item(client.contract.remove_cart_body or {}, item),
    )


def submit_order(client) -> None:
    """Submit an order through API only when the contract explicitly supports it."""
    if not client.contract.submit_order_url:
        raise TawreedApiUnavailable("No trusted Tawreed order-submit API contract.")
    _post_json(client, client.contract.submit_order_url, client.contract.submit_order_body or {})


__all__ = [
    "body_with_query",
    "body_with_match",
    "body_with_item",
    "search_products",
    "get_store_details",
    "add_to_cart",
    "remove_cart_item",
    "submit_order",
]
