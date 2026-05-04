"""Tawreed API payload selection and validation helpers."""

from __future__ import annotations
from typing import Any

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
