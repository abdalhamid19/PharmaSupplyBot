"""Read-only queries powering the Run Results (database) Streamlit tab.

Every query here is a SELECT against the order-runs analytics database. Writes
stay in ``order_runs_store`` so the GUI can never corrupt run history. SQL
statements live in :mod:`src.core.database.order_runs_read_sql`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .database import get_db_manager
from .order_runs_paths import default_order_runs_db
from .order_runs_read_sql import (
    ITEM_STORES,
    LIST_RUNS,
    MISSED_DISCOUNT,
    QUERY_COLUMNS,
    RUN_FACTS,
    RUN_STORE_ROW_COUNT,
)


def order_runs_connection(path: str | Path | None = None):
    """Return the shared manager for the order-runs database.

    The GUI only issues SELECTs; schema bootstrap in the manager is idempotent.
    ``path`` exists for tests; production callers use the resolved default.
    """
    return get_db_manager(path if path is not None else default_order_runs_db())


def _rows_as_dicts(rows: list, columns: list[str]) -> list[dict[str, Any]]:
    """Zip flat sqlite rows with column names into dict rows."""
    return [dict(zip(columns, row)) for row in rows]


def fetch_runs(limit: int | None = None, db=None) -> list[dict[str, Any]]:
    """Return the run list with per-run aggregates from the summary view."""
    rows = order_runs_connection(db).execute_query(LIST_RUNS, ())
    dicts = _rows_as_dicts(rows, QUERY_COLUMNS["runs"])
    return dicts if limit is None else dicts[:limit]


def fetch_run_items(run_key: str, db=None) -> list[dict[str, Any]]:
    """Return per-item facts for one run, joined to the item dimension."""
    rows = order_runs_connection(db).execute_query(RUN_FACTS, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


def fetch_item_stores(
    run_key: str, item_key: str, db=None
) -> list[dict[str, Any]]:
    """Return every offering-store snapshot row for one run item."""
    rows = order_runs_connection(db).execute_query(
        ITEM_STORES, (run_key, item_key)
    )
    return _rows_as_dicts(rows, QUERY_COLUMNS["stores"])


def fetch_missed_discounts(
    run_key: str | None = None, db=None
) -> list[dict[str, Any]]:
    """Return items whose winner had a lower discount than the best store.

    This is the analytics payoff of ``run_item_stores``: quantifying how much
    discount the strategy left on the table per item and run.
    """
    query, params = _missed_discount_query(run_key)
    rows = order_runs_connection(db).execute_query(query, params)
    return _rows_as_dicts(rows, QUERY_COLUMNS["missed"])


def _missed_discount_query(run_key: str | None) -> tuple[str, tuple]:
    """Scope the missed-discount query to one run when a key is given."""
    if not run_key:
        return MISSED_DISCOUNT, ()
    scoped = MISSED_DISCOUNT.replace(
        "where b.best_discount", "where w.run_key = ? and b.best_discount"
    )
    return scoped, (run_key,)


def run_store_row_count(run_key: str, db=None) -> int:
    """Return how many offering-store snapshot rows exist for one run."""
    rows = order_runs_connection(db).execute_query(RUN_STORE_ROW_COUNT, (run_key,))
    return int(rows[0][0]) if rows else 0


def database_is_ready(db=None) -> bool:
    """Return whether the order-runs database exists and is readable."""
    try:
        rows = order_runs_connection(db).execute_query(
            "select 1 from schema_meta limit 1", ()
        )
        return bool(rows)
    except Exception:
        return False
