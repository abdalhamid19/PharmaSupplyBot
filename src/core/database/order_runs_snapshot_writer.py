"""Snapshot write operations for offering stores and their dimensions.

Provided as a mixin so :class:`OrderRunsStore` stays a facade. All writes for
one item happen inside the same transaction the item fact uses, so an item and
its stores are always consistent with each other.
"""

from __future__ import annotations

from typing import Any

from .order_runs_store_sql import (
    DELETE_RUN_ITEM_STORES,
    SELECT_RUN_ITEM_STORE_COUNT,
    UPSERT_PRODUCT,
    UPSERT_RUN_ITEM_STORE,
    UPSERT_STORE,
)
from .order_runs_stores import (
    product_dimension_row,
    store_dimension_row,
    store_snapshot_rows,
    usable_store_rows,
)


class OrderRunsSnapshotMixin:
    """Offering-store snapshot writes for the order-runs database."""

    def count_run_item_stores(self, run_key: str, item_key: str) -> int:
        """Return how many offering stores are stored for one run item."""
        rows = self.db.execute_query(SELECT_RUN_ITEM_STORE_COUNT, (run_key, item_key))
        return int(rows[0][0]) if rows else 0

    def _write_store_snapshot(self, conn, plan) -> None:
        """Replace one item's offering-store snapshot inside an open transaction.

        Rows are deleted first so a retry that finds fewer stores leaves no
        stale ones behind — an UPSERT alone would keep them forever.
        """
        usable = usable_store_rows(plan.stores)
        conn.execute(
            DELETE_RUN_ITEM_STORES,
            {"run_key": plan.run_key, "item_key": plan.item_key},
        )
        if usable:
            _insert_snapshot(conn, plan, usable)


def _insert_snapshot(conn, plan, usable: list[dict[str, Any]]) -> None:
    """Insert store and product dimensions, then the snapshot fact rows."""
    conn.executemany(
        UPSERT_STORE, [store_dimension_row(store, plan.now) for store in usable]
    )
    conn.executemany(
        UPSERT_PRODUCT, [product_dimension_row(store, plan.now) for store in usable]
    )
    conn.executemany(
        UPSERT_RUN_ITEM_STORE,
        store_snapshot_rows(
            plan.run_key, plan.item_key, usable, plan.selections, plan.now, plan.source
        ),
    )


def snapshot_fact_fields(stores: Any, selections: Any) -> dict[str, Any]:
    """Return ``run_items`` fields derived from the offering-store snapshot."""
    from ..matching.candidate_identity import candidate_store_product_id
    from ..ordering.store_identity import store_identity_key
    from .order_runs_store_ranking import winner_product_id

    usable = usable_store_rows(stores)
    winner_id = winner_product_id(selections)
    winner = next(
        (s for s in usable if candidate_store_product_id(s) == winner_id), None
    )
    fields: dict[str, Any] = {"stores_offering": len(usable)}
    if winner is not None:
        fields["winner_store_key"] = store_identity_key(winner)
        fields["winner_store_product_id"] = winner_id
    return fields


__all__ = ["OrderRunsSnapshotMixin", "snapshot_fact_fields"]
