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
