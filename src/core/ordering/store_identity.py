"""Store-level identity helpers shared by matching, artifacts, and persistence.

``storeProductId`` identifies one *product inside one store*, so it must never
be used as a store identity: a single warehouse gets a different
``storeProductId`` for every product it sells. Using it as a store key would
create one "store" row per product and silently break every aggregation that
groups by warehouse. The keys below are store-level only.
"""

from __future__ import annotations

from typing import Any

STORE_ID_KEYS = ("storeId", "supplierId", "warehouseId", "branchId", "sellerId")
STORE_NAME_KEYS = (
    "storeName", "storeNameAr", "storeNameEn", "supplierName", "supplierNameAr",
    "supplierNameEn", "warehouseName", "warehouseNameAr", "warehouseNameEn",
    "pharmacyName", "branchName", "sellerName", "companyName",
)
NESTED_STORE_KEYS = ("store", "supplier", "warehouse", "pharmacy", "branch", "seller")
NESTED_NAME_KEYS = ("name", "nameAr", "nameEn", "arabicName", "englishName", "title")
_PLACEHOLDER_VALUES = {"", "none", "nan", "null"}


def store_identity_key(store: dict[str, Any]) -> str:
    """Return a stable store-level identity, never a product-level id.

    Returns an empty string when the payload carries neither a store id nor a
    usable name, which signals the caller to skip the row instead of inventing
    a synthetic warehouse.
    """
    for key in STORE_ID_KEYS:
        value = _clean_identifier(store.get(key))
        if value:
            return f"{key}:{value}"
    name = store_display_name(store)
    return f"storeName:{name}" if name else ""


def store_display_name(store: dict[str, Any]) -> str:
    """Return a normalized human-readable store, supplier, or warehouse name."""
    direct = _first_text(store, STORE_NAME_KEYS)
    if direct:
        return direct
    for object_key in NESTED_STORE_KEYS:
        nested = store.get(object_key)
        if isinstance(nested, dict):
            nested_name = _first_text(nested, NESTED_NAME_KEYS)
            if nested_name:
                return nested_name
    return ""


def _clean_identifier(value: object) -> str:
    """Return a normalized id, dropping Excel ``.0`` suffixes and placeholders."""
    text = _normalized_text(value)
    if text.lower() in _PLACEHOLDER_VALUES:
        return ""
    return text[:-2] if text.endswith(".0") else text


def _first_text(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-placeholder scalar text value for the given keys."""
    for key in keys:
        value = source.get(key)
        if isinstance(value, (dict, list, tuple)):
            continue
        text = _normalized_text(value)
        if text and text.lower() not in _PLACEHOLDER_VALUES:
            return text
    return ""


def _normalized_text(value: object) -> str:
    """Collapse whitespace so the same store stays stable across runs."""
    return " ".join(str(value if value is not None else "").split())


__all__ = [
    "STORE_ID_KEYS",
    "STORE_NAME_KEYS",
    "NESTED_STORE_KEYS",
    "NESTED_NAME_KEYS",
    "store_identity_key",
    "store_display_name",
]
