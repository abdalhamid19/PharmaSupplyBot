"""Results tab composition for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path
import shutil

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


def clear_profile_result_data(profile_key: str) -> int:
    """Delete files and subdirectories under one profile artifact directory."""
    artifact_dir = ARTIFACTS_DIR / profile_key
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        return 0
    removed_count = 0
    for path in safe_profile_artifact_paths(artifact_dir):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed_count += 1
    return removed_count


def safe_profile_artifact_paths(artifact_dir: Path) -> list[Path]:
    """Return direct children that are safe to remove from a profile artifact directory."""
    artifacts_root = ARTIFACTS_DIR.resolve(strict=False)
    resolved_artifact_dir = artifact_dir.resolve(strict=False)
    if resolved_artifact_dir.parent != artifacts_root:
        raise ValueError(f"Refusing to clear non-profile artifact path: {artifact_dir}")
    return list(artifact_dir.iterdir())


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
    if not artifact_dir.exists():
        st.info("No artifact files found.")
        return
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
