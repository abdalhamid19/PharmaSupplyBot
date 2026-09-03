"""Store-row selection and ranking for order-run snapshots.

Decides which Tawreed store rows can be persisted at all, and precomputes the
discount rank and the ordered/winner lookups the fact rows need.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..matching.candidate_identity import candidate_store_product_id
from ..ordering.store_identity import store_identity_key
from .order_runs_store_values import (
    discount_percent_value,
    is_synthetic_product_id,
    ordered_quantity_by_product,
)


def usable_store_rows(stores: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return store rows that can be persisted, de-duplicated by product id.

    Rows without an orderable Tawreed id, synthetic DOM-fallback rows, and rows
    with no resolvable store identity are dropped: they cannot key the
    ``products`` or ``stores`` dimensions, and counting them would inflate
    warehouse statistics with placeholders.
    """
    unique: dict[str, dict[str, Any]] = {}
    for store in stores or []:
        product_id = candidate_store_product_id(store)
        if not product_id or is_synthetic_product_id(product_id):
            continue
        if not store_identity_key(store):
            continue
        unique.setdefault(product_id, store)
    return list(unique.values())


def discount_ranks(stores: list[dict[str, Any]]) -> dict[str, int]:
    """Return 1-based discount ranks per product id, highest discount first."""
    ordered = sorted(stores, key=discount_percent_value, reverse=True)
    return {
        candidate_store_product_id(store): index
        for index, store in enumerate(ordered, start=1)
    }


def winner_product_id(selections: Iterable[tuple[dict[str, Any], int]]) -> str:
    """Return the product id of the first store the strategy selected."""
    for store, _ in selections or []:
        product_id = candidate_store_product_id(store)
        if product_id:
            return product_id
    return ""


def snapshot_context(
    stores: Iterable[dict[str, Any]],
    selections: Iterable[tuple[dict[str, Any], int]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return usable store rows plus the lookups each fact row needs."""
    usable = usable_store_rows(stores)
    return usable, {
        "ordered": ordered_quantity_by_product(selections),
        "winner_id": winner_product_id(selections),
        "ranks": discount_ranks(usable),
    }


__all__ = [
    "usable_store_rows",
    "discount_ranks",
    "winner_product_id",
    "snapshot_context",
]
