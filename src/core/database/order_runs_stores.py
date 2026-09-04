"""Fact-row builder for the ``run_item_stores`` table.

One row per offering store per item per run, with the strategy's choice flagged
and the discount rank precomputed so queries never need a window function.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

from ..matching.candidate_identity import candidate_store_product_id
from ..ordering.store_identity import store_identity_key
from ..pricing import DEFAULT_EXCEL_PRICE_MEANING, SourceKind
from .order_runs_dimensions import product_dimension_row, store_dimension_row
from .order_runs_store_ranking import snapshot_context, usable_store_rows
from .order_runs_store_values import store_price_fields
from .order_runs_values import as_int, as_text

_SOURCE_FROM_KIND: dict[str, SourceKind] = {
    "excel_target": "excel_target",
    "excel-target": "excel_target",
    "store_details": "tawreed",
    "search": "tawreed",
}


def _source_kind_from_source(source: str) -> SourceKind:
    """Translate a ``run_item_stores.source`` value to the resolver's source_kind."""
    return _SOURCE_FROM_KIND.get(source or "", "tawreed")


def store_snapshot_rows(
    run_key: str,
    item_key: str,
    stores: Iterable[dict[str, Any]],
    selections: Iterable[tuple[dict[str, Any], int]],
    now: str,
    source: str = "",
    excel_price_meaning: Literal[
        "public_with_discount", "purchase_only", "public_only"
    ] = DEFAULT_EXCEL_PRICE_MEANING,
) -> list[dict[str, Any]]:
    """Return one ``run_item_stores`` row per offering store."""
    usable, context = snapshot_context(stores, selections)
    keys = {"run_key": run_key, "item_key": item_key, "source": as_text(source)}
    kind = _source_kind_from_source(source)
    return [
        _snapshot_row(
            store,
            keys,
            now,
            context,
            source_kind=kind,
            excel_price_meaning=_candidate_meaning(store, excel_price_meaning),
        )
        for store in usable
    ]


def _candidate_meaning(
    store: dict[str, Any],
    fallback: Literal[
        "public_with_discount", "purchase_only", "public_only"
    ],
) -> Literal["public_with_discount", "purchase_only", "public_only"]:
    """Return the per-row ``priceMeaning`` if the candidate carries one."""
    meaning = store.get("priceMeaning")
    if meaning in {"public_with_discount", "purchase_only", "public_only"}:
        return meaning
    return fallback


def _snapshot_row(
    store: dict[str, Any],
    keys: dict[str, str],
    now: str,
    context: dict[str, Any],
    *,
    source_kind: SourceKind = "tawreed",
    excel_price_meaning: Literal[
        "public_with_discount", "purchase_only", "public_only"
    ] = DEFAULT_EXCEL_PRICE_MEANING,
) -> dict[str, Any]:
    """Return one fact row for a single offering store."""
    product_id = candidate_store_product_id(store)
    row = dict(keys)
    row["store_product_id"] = product_id
    row["store_key"] = store_identity_key(store)
    row["captured_at"] = now
    row.update(_selection_fields(product_id, context))
    row.update(_stock_fields(store))
    row.update(
        store_price_fields(
            store,
            source_kind=source_kind,
            excel_price_meaning=excel_price_meaning,
        )
    )
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
