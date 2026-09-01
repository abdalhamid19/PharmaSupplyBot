"""KPI drill-down button row for the Run Results (database) tab."""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def render_drilldown_buttons(run: dict[str, Any], items: list[dict[str, Any]]) -> None:
    """Render KPI cards as buttons that open category-filtered modals."""
    run_key = run["run_key"]
    with st.container(horizontal=True):
        for label, count, icon, opener in _kpi_specs(run, items, run_key):
            if count <= 0:
                continue
            if st.button(
                f"{label} · {count}",
                icon=icon,
                use_container_width=True,
                key=f"drill_{label.replace(' ', '_')}_{run_key}",
            ):
                opener()


def _kpi_specs(run, items, run_key):
    """Return (label, count, icon, open) tuples for the KPI button row."""
    from . import streamlit_run_drilldown_dialogs as _d
    return [
        ("Items", len(items), ":material/list:",
         lambda: _d.show_all_items_dialog(items)),
        ("Matched", int(run.get("matched", 0) or 0), ":material/check_circle:",
         lambda: _d.show_matched_dialog(run_key)),
        ("Flagged", int(run.get("flagged", 0) or 0), ":material/warning:",
         lambda: _d.show_flagged_dialog(run_key)),
        ("Offering stores", _stores_count(run, run_key), ":material/store:",
         lambda: _d.show_offering_stores_dialog(items, run_key)),
        ("Ordered qty", int(run.get("total_ordered", 0) or 0),
         ":material/shopping_cart:",
         lambda: _d.show_ordered_dialog(run_key)),
    ]


def _stores_count(run: dict[str, Any], run_key: str) -> int:
    """Resolve the offering-stores count from the run row or a fallback query."""
    from ....core.database.order_runs_read import run_store_row_count

    return int(run.get("store_count", 0) or 0) or run_store_row_count(run_key)