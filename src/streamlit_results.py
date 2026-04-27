"""Results tab composition for the Streamlit GUI."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .streamlit_shared import (
    ARTIFACTS_DIR,
    load_csv_rows,
    load_xlsx_rows,
    profile_selector_options,
    summary_csv_path,
    summary_xlsx_path,
)
from .streamlit_summary_views import render_summary_views
from .streamlit_timing_view import render_timing_metrics


def render_results_tab(default_profile: str | None) -> None:
    """Render summary/result browsing tools."""
    st.subheader("Results")
    if not default_profile:
        st.warning("No profiles found in config.")
        return
    profile_key = st.selectbox("Artifacts profile", profile_selector_options(), index=0)
    render_selected_profile_results(profile_key)


def render_selected_profile_results(profile_key: str) -> None:
    """Render summary and artifacts for one selected profile."""
    summary_rows, summary_xlsx_rows = summary_sources(profile_key)
    if not summary_rows and not summary_xlsx_rows:
        st.info(f"No summary files found for `{profile_key}`.")
    else:
        render_profile_summaries(profile_key, summary_rows, summary_xlsx_rows)
        render_timing_metrics(summary_rows or summary_xlsx_rows)
    render_recent_artifact_files(profile_key)


def summary_sources(profile_key: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return the CSV and XLSX summary row sets for one profile."""
    return (
        load_csv_rows(summary_csv_path(profile_key)),
        load_xlsx_rows(summary_xlsx_path(profile_key)),
    )


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


def render_recent_artifact_files(profile_key: str) -> None:
    """Render the recent artifact files table for one profile."""
    st.subheader("Recent Artifact Files")
    artifact_dir = ARTIFACTS_DIR / profile_key
    artifact_files = sorted(
        artifact_dir.glob("*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not artifact_files:
        st.info("No artifact files found.")
        return
    rows = [
        {"name": path.name, "size_kb": round(path.stat().st_size / 1024, 1)}
        for path in artifact_files[:30]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
