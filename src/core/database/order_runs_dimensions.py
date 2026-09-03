"""Dimension row builders for stores and Tawreed products.

Kept separate from fact-row building so each module stays small and the
identity rules (which must never drift) sit next to each other.
"""

from __future__ import annotations

from typing import Any

from ..matching.candidate_identity import candidate_store_product_id
from ..ordering.store_identity import store_display_name, store_identity_key
from .order_runs_store_values import is_synthetic_product_id
from .order_runs_values import as_text


def store_dimension_row(store: dict[str, Any], now: str) -> dict[str, Any]:
    """Return one ``stores`` dimension row.

    The key comes from :func:`store_identity_key`, which excludes
    ``storeProductId`` so one warehouse stays one row rather than forking once
    per product it sells.
    """
    return {
        "store_key": store_identity_key(store),
        "store_name": store_display_name(store),
        "first_seen_at": now,
        "last_seen_at": now,
    }


def product_dimension_row(store: dict[str, Any], now: str) -> dict[str, Any]:
    """Return one ``products`` dimension row.

    ``is_synthetic`` marks DOM-fallback placeholders so analytics can exclude
    products that never existed in Tawreed's catalogue.
    """
    product_id = candidate_store_product_id(store)
    return {
        "store_product_id": product_id,
        "product_id": as_text(store.get("productId") or store.get("id")),
        "name_ar": as_text(store.get("productName")),
        "name_en": as_text(
            store.get("productNameEn") or store.get("productNameEnFallback")
        ),
        "is_synthetic": int(is_synthetic_product_id(product_id)),
        "first_seen_at": now,
        "last_seen_at": now,
    }


__all__ = ["store_dimension_row", "product_dimension_row"]
