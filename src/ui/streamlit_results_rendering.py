"""Rendering functions for results tab."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.order_ai_run_summary import summarize_order_ai_rows
from .streamlit_shared import (
    ARTIFACTS_DIR,
    load_csv_rows,
    summary_csv_path,
    summary_xlsx_path,
)
from .streamlit_summary_views import render_summary_views
from .streamlit_timing_view import render_timing_metrics
from .streamlit_results_tables import (
    render_run_table,
    render_order_ai_trace_summary,
    render_recent_run_files,
    render_recent_artifact_files,
)


def render_command_run_results() -> bool:
    """Render new command/profile/run artifact folders when present."""
    from .streamlit_results_selection import command_options, command_profile_options, command_run_options
    commands = command_options()
    if not commands:
        return False
    command = st.selectbox("Command", commands, index=0)
    profile_key = st.selectbox("Profile", command_profile_options(command), index=0)
    run_id = st.selectbox("Run", command_run_options(command, profile_key), index=0)
    run_dir = ARTIFACTS_DIR / command / profile_key / run_id
    render_run_dir_results(command, profile_key, run_dir)
    return True


def render_run_dir_results(command: str, profile_key: str, run_dir: Path) -> None:
    """Render files and summaries from one command run directory."""
    st.caption(f"{command} / {profile_key} / {run_dir.name}")
    summary_rows = run_summary_rows(run_dir)
    if summary_rows:
        render_timing_metrics(summary_rows)
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    render_run_table(run_dir, "Order AI Trace", "order_ai_trace_*.csv")
    render_recent_run_files(run_dir)


def run_summary_rows(run_dir: Path) -> list[dict[str, str]]:
    """Return rows from the preferred summary CSV in one run directory."""
    path = preferred_run_summary_path(run_dir)
    return load_csv_rows(path) if path else []


def preferred_run_summary_path(run_dir: Path) -> Path | None:
    """Return the most useful summary file for a command run."""
    for pattern in (
        "order_item_summary_*.csv",
        "match_only_summary_*.csv",
        "order_result_summary_*.csv",
        "*summary*.csv",
    ):
        paths = sorted(run_dir.glob(pattern))
        if paths:
            return paths[0]
    return None


def render_selected_profile_results(profile_key: str) -> None:
    """Render summary and artifacts for one selected profile."""
    from .streamlit_results_management import summary_sources, clear_profile_result_data
    render_clear_profile_results_controls(profile_key)
    summary_rows, summary_xlsx_rows = summary_sources(profile_key)
    if not summary_rows and not summary_xlsx_rows:
        st.info(f"No summary files found for `{profile_key}`.")
    else:
        render_profile_summaries(profile_key, summary_rows, summary_xlsx_rows)
        render_timing_metrics(summary_rows or summary_xlsx_rows)
    render_recent_artifact_files(profile_key)


def render_clear_profile_results_controls(profile_key: str) -> None:
    """Render controls that clear old result artifacts for the selected profile."""
    confirm_clear = st.checkbox(
        f"Confirm clearing old result data for `{profile_key}`",
        value=False,
        key=f"clear_results_confirm_{profile_key}",
    )
    if not st.button(
        "Clear Old Result Data",
        disabled=not confirm_clear,
        key=f"clear_results_button_{profile_key}",
    ):
        return
    removed_count = clear_profile_result_data(profile_key)
    st.success(f"Cleared {removed_count} old result file(s) for `{profile_key}`.")
    st.rerun()


def render_profile_summaries(
    profile_key: str,
    summary_rows: list[dict[str, str]],
    summary_xlsx_rows: list[dict[str, str]],
) -> None:
    """Render the summary tables for one selected profile."""
    render_summary_views(
        profile_key,
        summary_csv_path(profile_key),
        summary_rows,
        summary_xlsx_path(profile_key),
        summary_xlsx_rows,
    )


def render_fresh_run_analysis(rows: list[dict[str, str]]) -> None:
    """Render metrics for one fresh execution window."""
    st.subheader("Fresh Run Analysis")
    if not rows:
        st.warning("No new summary rows were appended by this run.")
        return
    render_timing_metrics(rows)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
