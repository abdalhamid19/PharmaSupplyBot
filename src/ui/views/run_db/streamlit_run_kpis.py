"""KPI metric cards for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_run_kpis(run: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """Render the headline metric row for one selected run.

    ``Matched``/``Flagged`` come from the ``v_run_summary`` aggregates (which
    exclude ``not-orderable`` catalog matches) rather than re-counting raw
    item flags, so the cards agree with the run picker and any SQL client.
    """
    stores_rows = _store_count(run["run_key"])
    matched = int(run.get("matched", 0) or 0)
    flagged = int(run.get("flagged", 0) or 0)
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


def _store_count(run_key: str) -> int:
    """Return how many offering-store rows exist for one run."""
    from ....core.database.order_runs_read import run_store_row_count

    return run_store_row_count(run_key)
