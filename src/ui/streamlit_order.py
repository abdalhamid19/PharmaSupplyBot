"""Order tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ..core.prevented_items import (
    DEFAULT_PREVENTED_ITEMS_PATH,
    is_prevented_items_excel_path,
)
from .streamlit_order_form import order_form_values
from .streamlit_order_process import render_running_order_controls, start_order_process
from .streamlit_order_paths import order_run_summary_csv_path, order_stop_flag_path
from .streamlit_order_state import prepare_order_state_files
from .streamlit_order_command import order_command
from .streamlit_shared import csv_row_count
from .streamlit_uploads import resolve_excel_path


def render_order_tab(
    app_config, default_profile: str | None, config_path: Path
) -> None:
    """Render order execution controls and fresh-run analysis."""
    st.subheader("Run Order")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    if render_running_order_controls():
        return
    submitted, form_values = order_form_values(app_config)
    if not submitted:
        return
    excel_path = resolve_excel_path(
        form_values["excel_path_str"], form_values["upload"]
    )
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    prevented_items_path = Path(
        str(form_values.get("prevented_items_excel") or DEFAULT_PREVENTED_ITEMS_PATH)
    )
    if is_prevented_items_excel_path(excel_path, prevented_items_path):
        st.error(
            "`drugprevented.xlsx` is the prevented-items list, not an order sheet. "
            "Please choose the shortage/order Excel file."
        )
        return
    run_order_submission(
        app_config, default_profile, config_path, form_values, excel_path
    )


def run_order_submission(
    app_config,
    default_profile: str,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> None:
    """Run one order submission and render its summary output."""
    if not prepare_order_state_files(app_config, form_values):
        return
    summary_path = order_run_summary_csv_path(default_profile, form_values)
    previous_row_count = csv_row_count(summary_path)
    command = order_command(config_path, form_values, excel_path)
    stop_flag_path = order_stop_flag_path()
    start_order_process(
        command, summary_path, previous_row_count, stop_flag_path, form_values
    )
    st.success("Order flow started. Use Stop Order to stop after the current item.")
    st.rerun()


__all__ = [
    "render_order_tab",
    "run_order_submission",
]
