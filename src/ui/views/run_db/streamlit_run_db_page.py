"""Run Results (database) tab: browse order-runs.sqlite from the GUI."""

from __future__ import annotations

import streamlit as st

from ....core.database.order_runs_read import (
    database_is_ready,
    fetch_run_items,
    fetch_runs,
)
from .streamlit_missed_discount import render_missed_discount_panel
from .streamlit_run_drilldown import (
    get_active_filter,
    render_kpi_filter_bar,
    resolve_filtered_rows,
)
from .streamlit_run_kpis import render_run_header
from .streamlit_run_tables import (
    render_item_stores_expander,
    render_run_items_table,
)


def render_run_db_tab() -> None:
    """Render the database-backed results browser."""
    st.title("Run Results (Database)")
    st.markdown(
        "Read-only view of `state/order_runs.db`: every run, its items, "
        "and the offering-store snapshots captured during ordering."
    )
    if not database_is_ready():
        _render_missing_database()
        return
    runs = fetch_runs()
    if not runs:
        st.info("No runs recorded yet — execute an order or match-only run.")
        return
    selected = _render_run_selector(runs)
    run = runs[selected]
    _render_selected_run(run)


def _render_run_selector(runs: list[dict]) -> int:
    """Render the run picker; newest runs first."""
    labels = [
        f"{row['run_key']}  ·  {row['items']} items  ·  {row['mode']}"
        for row in runs
    ]
    return st.selectbox(
        "Run",
        range(len(runs)),
        format_func=lambda index: labels[index],
    )


def _render_selected_run(run: dict) -> None:
    """Render KPIs, item facts, store snapshots, and missed discounts."""
    render_run_header(run)
    items = fetch_run_items(run["run_key"])
    render_kpi_filter_bar(run, items)
    active = get_active_filter(run["run_key"])
    rows, caption = resolve_filtered_rows(run["run_key"], active, items)
    render_run_items_table(rows, caption=caption)
    render_item_stores_expander(items, run["run_key"])
    st.divider()
    render_missed_discount_panel(run["run_key"])


def _render_missing_database() -> None:
    """Explain what to do when the analytics database is absent."""
    st.warning(
        "The order-runs database was not found or has no schema yet. "
        "Set `ORDER_RUNS_DB_PATH` or run an order from the Order tab first."
    )
