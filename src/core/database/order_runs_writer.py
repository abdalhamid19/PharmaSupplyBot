"""Write operations for order-run lifecycle and item facts.

Provided as a mixin so :class:`OrderRunsStore` stays a thin facade while the
transaction handling lives in one focused module. Every write is a single short
transaction with ``BEGIN IMMEDIATE`` so parallel item workers queue on the
write lock instead of failing mid-transaction with ``SQLITE_BUSY``.
"""

from __future__ import annotations

from typing import Any

from .order_runs_keys import item_dimension_row
from .order_runs_rows import run_item_row
from .order_runs_sql import (
    FINISH_RUN,
    SELECT_RUN_EXISTS,
    SELECT_RUN_ITEM_COUNT,
    UPSERT_ITEM,
    UPSERT_RUN,
    UPSERT_RUN_ITEM,
)
from .order_runs_time import utc_now


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
        **fact_fields: Any,
    ) -> None:
        """Persist one item's dimension and fact rows in a single transaction."""
        timestamp = now or utc_now()
        item = item_dimension_row(
            summary.get("item_code"), summary.get("item_name"), timestamp
        )
        fact = run_item_row(run_key, summary, **fact_fields)
        self._write(lambda conn: _write_item(conn, item, fact))

    def count_run_items(self, run_key: str) -> int:
        """Return how many item facts are stored for one run."""
        rows = self.db.execute_query(SELECT_RUN_ITEM_COUNT, (run_key,))
        return int(rows[0][0]) if rows else 0

    def run_exists(self, run_key: str) -> bool:
        """Return whether a run record has already been opened."""
        return bool(self.db.execute_query(SELECT_RUN_EXISTS, (run_key,)))

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


def _write_item(conn, item: dict[str, Any], fact: dict[str, Any]) -> None:
    """Insert the item dimension before the fact row that references it."""
    conn.execute(UPSERT_ITEM, item)
    conn.execute(UPSERT_RUN_ITEM, fact)


__all__ = ["OrderRunsWriterMixin"]
