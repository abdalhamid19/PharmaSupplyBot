"""Order tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_order_form import order_form_values
from .streamlit_process import render_command_result, run_cli_subprocess
from .streamlit_results import render_fresh_run_analysis
from .streamlit_shared import csv_row_count, load_new_summary_rows, summary_csv_path
from .streamlit_uploads import resolve_excel_path


def render_order_tab(app_config, default_profile: str | None, config_path: Path) -> None:
    """Render order execution controls and fresh-run analysis."""
    st.subheader("Run Order")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    submitted, form_values = order_form_values(app_config)
    if not submitted:
        return
    excel_path = resolve_excel_path(form_values["excel_path_str"], form_values["upload"])
    if excel_path is None:
        st.error("Please choose or upload an Excel file.")
        return
    run_order_submission(default_profile, config_path, form_values, excel_path)


def run_order_submission(
    default_profile: str,
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> None:
    """Run one order submission and render its summary output."""
    summary_path = summary_csv_path(default_profile)
    previous_row_count = csv_row_count(summary_path)
    command = order_command(config_path, form_values, excel_path)
    with st.spinner("Running Tawreed order flow..."):
        result = run_cli_subprocess(command)
    render_command_result(result)
    render_fresh_run_analysis(load_new_summary_rows(summary_path, previous_row_count))


def order_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path,
) -> list[str]:
    """Return the CLI command arguments for one order run."""
    command = ["order", "--config", str(config_path), "--excel", str(excel_path)]
    command.extend(["--limit", str(form_values["limit"])])
    if form_values["profile_mode"] == "Single profile":
        command.extend(["--profile", str(form_values["profile_key"])])
    else:
        command.append("--all-profiles")
    if form_values["debug_browser"]:
        command.append("--debug-browser")
    return command
