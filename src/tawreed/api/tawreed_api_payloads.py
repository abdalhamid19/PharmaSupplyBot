"""Request payload helpers for discovered Tawreed API endpoints."""

from __future__ import annotations

import json
from typing import Any

from ...core.candidate_identity import candidate_store_product_id


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
# Selection helpers (from tawreed_selections.py)
# ============================================================================

def first_text_field(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string-like value for the provided keys."""
    for key in keys:
        val = source.get(key)
        if isinstance(val, (dict, list, tuple)): continue
        text = str(val or "").strip()
        if text: return text
    return ""

def first_nested_text_field(
    source: dict[str, Any],
    object_keys: tuple[str, ...],
    name_keys: tuple[str, ...],
) -> str:
    """Return the first non-empty nested store/supplier name value."""
    for o_key in object_keys:
        nested = source.get(o_key)
        if not isinstance(nested, dict): continue
        text = first_text_field(nested, name_keys)
        if text: return text
    return ""

def looks_like_product_payload(source: dict[str, Any]) -> bool:
    """Return whether the payload is a product row rather than a store row."""
    return any(k in source for k in ("productName", "productNameEn", "storeProductId"))

def stores_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized stores rows from a store-details payload."""
    return list(payload.get("data", []) or [])


__all__ = [
    "body_with_query",
    "body_with_match",
    "body_with_item",
    "first_text_field",
    "first_nested_text_field",
    "looks_like_product_payload",
    "stores_from_payload",
]
