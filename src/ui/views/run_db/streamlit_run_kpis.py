"""KPI metric cards for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_run_kpis(run: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """Render the headline metric row for one selected run."""
    stores_rows = _store_count(run["run_key"])
    matched = _sum_or_zero(items, lambda i: bool(i["matched"]))
    flagged = _sum_or_zero(items, lambda i: bool(i["manual_review_required"]))
    with st.container(horizontal=True):
        st.metric("Items", len(items), border=True)
        st.metric("Matched", matched, border=True)
        st.metric("Flagged", flagged, border=True)
        st.metric("Offering stores", stores_rows, border=True)
        st.metric("Ordered qty", run.get("total_ordered", 0), border=True)


def render_run_header(run: dict[str, Any]) -> None:
    """Render run identity above the KPI row."""
    st.subheader(f"{run['profile_key']} / {run['run_id']}")
    st.caption(
        f"mode={run.get('mode', '')} · command={run.get('command', '')} · "
        f"started={run.get('started_at', '')} · finished={run.get('finished_at', '-')}"
    )


def _sum_or_zero(items: list[dict[str, Any]], predicate) -> int:
    """Sum predicate hits across item rows (sqlite returns 0/1 ints)."""
    return sum(1 for item in items if predicate(item))


def _store_count(run_key: str) -> int:
    """Return how many offering-store rows exist for one run."""
    from ....core.database.order_runs_read import run_store_row_count

    return run_store_row_count(run_key)
