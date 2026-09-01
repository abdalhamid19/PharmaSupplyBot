"""Modal dialogs for KPI drill-down buttons on the Run Results (database) tab."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .streamlit_run_tables import render_item_stores_expander, render_run_items_table


def _render_rows(rows: list[dict[str, Any]]) -> None:
    """Render a drill-down table or a friendly empty state."""
    if not rows:
        st.info("No items in this category.")
        return
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


@st.dialog("Matched items")
def show_matched_dialog(run_key: str) -> None:
    """Show every matched item for ``run_key``."""
    from ....core.database.order_runs_read import fetch_run_items_matched

    _render_rows(fetch_run_items_matched(run_key))


@st.dialog("Flagged items")
def show_flagged_dialog(run_key: str) -> None:
    """Show every flagged item for ``run_key``."""
    from ....core.database.order_runs_read import fetch_run_items_flagged

    _render_rows(fetch_run_items_flagged(run_key))


@st.dialog("Not-orderable items")
def show_not_orderable_dialog(run_key: str) -> None:
    """Show every not-orderable item for ``run_key``."""
    from ....core.database.order_runs_read import fetch_run_items_not_orderable

    _render_rows(fetch_run_items_not_orderable(run_key))


@st.dialog("Ordered items")
def show_ordered_dialog(run_key: str) -> None:
    """Show every ordered item for ``run_key``."""
    from ....core.database.order_runs_read import fetch_run_items_ordered

    _render_rows(fetch_run_items_ordered(run_key))


def show_all_items_dialog(items: list[dict[str, Any]]) -> None:
    """Show the unfiltered item table inside a modal."""

    @st.dialog("Items")
    def _dialog() -> None:
        render_run_items_table(items)

    _dialog()


def show_offering_stores_dialog(items: list[dict[str, Any]], run_key: str) -> None:
    """Show the offering-store snapshot expander inside a modal."""

    @st.dialog("Offering stores")
    def _dialog() -> None:
        render_item_stores_expander(items, run_key)

    _dialog()