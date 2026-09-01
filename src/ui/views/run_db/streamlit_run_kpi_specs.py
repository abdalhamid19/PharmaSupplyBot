"""KPI category metadata for the Run DB in-page filter bar.

Keeping the label / fetcher-name maps in their own module lets the
``streamlit_run_drilldown`` view stay under the 100-line cap while
sharing a single source of truth for category lookups.
"""

from __future__ import annotations

KPI_LABELS: dict[str, str] = {
    "matched": "Matched",
    "flagged": "Flagged",
    "not_orderable": "Not-orderable",
    "ordered": "Ordered qty",
}

FETCHER_NAMES: dict[str, str] = {
    "matched": "fetch_run_items_matched",
    "flagged": "fetch_run_items_flagged",
    "not_orderable": "fetch_run_items_not_orderable",
    "ordered": "fetch_run_items_ordered",
}


def state_key(run_key: str) -> str:
    """Session-state key for the active KPI filter on a given run."""
    return f"kpi_filter_{run_key.replace('/', '_')}"


__all__ = ["KPI_LABELS", "FETCHER_NAMES", "state_key"]
