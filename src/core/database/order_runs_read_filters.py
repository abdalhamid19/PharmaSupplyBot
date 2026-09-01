"""Read functions for the Run Results (database) KPI-card drilldown modals.

Each query mirrors the column shape of ``RUN_FACTS`` and uses the same
``items`` column map so the modal rows line up with the parent table.
"""

from __future__ import annotations

from typing import Any

from .order_runs_read import _rows_as_dicts, order_runs_connection
from .order_runs_read_filters_sql import (
    RUN_ITEMS_FLAGGED,
    RUN_ITEMS_MATCHED,
    RUN_ITEMS_NOT_ORDERABLE,
    RUN_ITEMS_ORDERED,
)
from .order_runs_read_sql import QUERY_COLUMNS


def fetch_run_items_matched(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where matched=1 AND status != 'not-orderable'."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_MATCHED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


def fetch_run_items_flagged(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where flagged=1."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_FLAGGED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


def fetch_run_items_not_orderable(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where status = 'not-orderable'."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_NOT_ORDERABLE, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


def fetch_run_items_ordered(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where ordered_qty > 0."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_ORDERED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


__all__ = [
    "fetch_run_items_flagged",
    "fetch_run_items_matched",
    "fetch_run_items_not_orderable",
    "fetch_run_items_ordered",
]