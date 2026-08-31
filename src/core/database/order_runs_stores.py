"""Fact-row builder for the ``run_item_stores`` table.

One row per offering store per item per run, with the strategy's choice flagged
and the discount rank precomputed so queries never need a window function.
"""

from __future__ import annotations

from typing import Any, Iterable

from ..matching.candidate_identity import candidate_store_product_id
from ..ordering.store_identity import store_identity_key
from .order_runs_dimensions import product_dimension_row, store_dimension_row
from .order_runs_store_ranking import snapshot_context, usable_store_rows
from .order_runs_store_values import store_price_fields
from .order_runs_values import as_int, as_text


def store_snapshot_rows(
    run_key: str,
    item_key: str,
    stores: Iterable[dict[str, Any]],
    selections: Iterable[tuple[dict[str, Any], int]],
    now: str,
    source: str = "",
) -> list[dict[str, Any]]:
    """Return one ``run_item_stores`` row per offering store."""
    usable, context = snapshot_context(stores, selections)
    keys = {"run_key": run_key, "item_key": item_key, "source": as_text(source)}
    return [_snapshot_row(store, keys, now, context) for store in usable]


def _snapshot_row(
    store: dict[str, Any],
    keys: dict[str, str],
    now: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Return one fact row for a single offering store."""
    product_id = candidate_store_product_id(store)
    row = dict(keys)
    row["store_product_id"] = product_id
    row["store_key"] = store_identity_key(store)
    row["captured_at"] = now
    row.update(_selection_fields(product_id, context))
    row.update(_stock_fields(store))
    row.update(store_price_fields(store))
    return row


def _selection_fields(product_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Return winner, ordered-quantity, and discount-rank fields."""
    winner_id = context["winner_id"]
    return {
        "is_winner": int(bool(winner_id) and product_id == winner_id),
        "ordered_qty": context["ordered"].get(product_id, 0),
        "rank_by_discount": context["ranks"].get(product_id),
    }


def _stock_fields(store: dict[str, Any]) -> dict[str, Any]:
    """Return availability and supplier-priority fields for one store."""
    return {
        "available_qty": as_int(store.get("availableQuantity")),
        "priority": as_int(store.get("priority")) or None,
    }


__all__ = [
    "store_snapshot_rows",
    "usable_store_rows",
    "store_dimension_row",
    "product_dimension_row",
]
