"""Request payload helpers for discovered Tawreed API endpoints."""

from __future__ import annotations

import json
from typing import Any

from ..core.candidate_identity import candidate_store_product_id


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
    candidate = getattr(match, "data", {}) or {}
    
    store_product_id = candidate_store_product_id(candidate)
    
    # Build correct payload structure based on discovered API
    payload["data"] = {
        "customerId": _extract_customer_id(),
        "storeProductId": int(store_product_id),
        "quantity": int(quantity),
        "typeId": 1  # Cart type (discovered from browser)
    }
    
    return payload


def _extract_customer_id() -> int:
    """Extract customer ID from JWT token in state file."""
    # This will be populated from token during API initialization
    # For now, return a placeholder that will be filled by TawreedApiClient
    return 0


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
