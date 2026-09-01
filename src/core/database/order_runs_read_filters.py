"""Cached read functions for the Run Results (database) KPI-card filter.

Each query mirrors the column shape of ``RUN_FACTS`` and uses the same
``items`` column map so the inline filter rows line up with the parent
table. ``@st.cache_data(ttl="5m")`` keeps reruns snappy when the user
clicks between KPI cards; the short TTL means a new order run will
invalidate naturally within minutes without a manual cache clear.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from .order_runs_read import _rows_as_dicts, order_runs_connection
from .order_runs_read_filters_sql import (
    RUN_ITEMS_FLAGGED,
    RUN_ITEMS_MATCHED,
    RUN_ITEMS_NOT_ORDERABLE,
    RUN_ITEMS_ORDERED,
)
from .order_runs_read_sql import QUERY_COLUMNS


@st.cache_data(ttl="5m", max_entries=32)
def fetch_run_items_matched(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where matched=1 AND status != 'not-orderable'."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_MATCHED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


@st.cache_data(ttl="5m", max_entries=32)
def fetch_run_items_flagged(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where flagged=1."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_FLAGGED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


@st.cache_data(ttl="5m", max_entries=32)
def fetch_run_items_not_orderable(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where status = 'not-orderable'."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_NOT_ORDERABLE, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


@st.cache_data(ttl="5m", max_entries=32)
def fetch_run_items_ordered(run_key: str, db=None) -> list[dict[str, Any]]:
    """Items where ordered_qty > 0."""
    rows = order_runs_connection(db).execute_query(RUN_ITEMS_ORDERED, (run_key,))
    return _rows_as_dicts(rows, QUERY_COLUMNS["items"])


def clear_filter_cache() -> None:
    """Drop every cached filter result (call after a new run is persisted)."""
    fetch_run_items_matched.clear()
    fetch_run_items_flagged.clear()
    fetch_run_items_not_orderable.clear()
    fetch_run_items_ordered.clear()


__all__ = [
    "clear_filter_cache",
    "fetch_run_items_flagged",
    "fetch_run_items_matched",
    "fetch_run_items_not_orderable",
    "fetch_run_items_ordered",
]
