"""Write operations for order-run lifecycle and item facts.

Provided as a mixin so :class:`OrderRunsStore` stays a thin facade while the
transaction handling lives in one focused module. Every write is a single short
transaction with ``BEGIN IMMEDIATE`` so parallel item workers queue on the
write lock instead of failing mid-transaction with ``SQLITE_BUSY``.
"""

from __future__ import annotations

from typing import Any

from .order_runs_sql import (
    FINISH_RUN,
    SELECT_RUN_EXISTS,
    SELECT_RUN_ITEM_COUNT,
    UPSERT_ITEM,
    UPSERT_RUN,
    UPSERT_RUN_ITEM,
)
from .order_runs_time import utc_now
from .order_runs_write_plan import item_write_plan


class OrderRunsWriterMixin:
    """Lifecycle and fact writes for the order-runs database."""

    def open_run(self, run_meta: dict[str, Any]) -> str:
        """Record the start of one run and return its run key."""
        self._write(lambda conn: conn.execute(UPSERT_RUN, run_meta))
        return str(run_meta["run_key"])

    def finish_run(self, run_key: str, finished_at: str | None = None) -> None:
        """Mark a run finished and derive ``total_items`` from its fact rows."""
        params = {"run_key": run_key, "finished_at": finished_at or utc_now()}
        self._write(lambda conn: conn.execute(FINISH_RUN, params))

    def upsert_run_item(
        self,
        run_key: str,
        summary: dict[str, Any],
        now: str | None = None,
        **fields: Any,
    ) -> None:
        """Persist one item, its dimensions, and its offering stores atomically.

        Keeping the snapshot in the same transaction as the item fact means
        ``stores_offering`` can never disagree with the rows it counts.
        """
        snapshot = {key: fields.pop(key, None) for key in _SNAPSHOT_KEYS}
        plan = item_write_plan(run_key, summary, now or utc_now(), snapshot, fields)
        self._write(lambda conn: self._write_plan(conn, plan))

    def count_run_items(self, run_key: str) -> int:
        """Return how many item facts are stored for one run."""
        rows = self.db.execute_query(SELECT_RUN_ITEM_COUNT, (run_key,))
        return int(rows[0][0]) if rows else 0

    def run_exists(self, run_key: str) -> bool:
        """Return whether a run record has already been opened."""
        return bool(self.db.execute_query(SELECT_RUN_EXISTS, (run_key,)))

    def _write_plan(self, conn, plan) -> None:
        """Write item dimension, item fact, then the offering-store snapshot."""
        conn.execute(UPSERT_ITEM, plan.item_row)
        conn.execute(UPSERT_RUN_ITEM, plan.fact_row)
        self._write_store_snapshot(conn, plan)

    def _write(self, operation) -> None:
        """Run one write inside a short immediate transaction."""
        with self.db.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                operation(conn)
                conn.commit()
            except Exception:
                conn.rollback()
                raise


_SNAPSHOT_KEYS = ("stores", "store_selections", "store_source")

__all__ = ["OrderRunsWriterMixin"]
