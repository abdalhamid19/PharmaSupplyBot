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
    if render_command_run_results():
        return
    profile_key = st.selectbox("Artifacts profile", profile_selector_options(), index=0)
    render_selected_profile_results(profile_key)


def render_command_run_results() -> bool:
    """Render new command/profile/run artifact folders when present."""
    commands = command_options()
    if not commands:
        return False
    command = st.selectbox("Command", commands, index=0)
    profile_key = st.selectbox("Profile", command_profile_options(command), index=0)
    run_id = st.selectbox("Run", command_run_options(command, profile_key), index=0)
    run_dir = ARTIFACTS_DIR / command / profile_key / run_id
    render_run_dir_results(command, profile_key, run_dir)
    return True


def command_options() -> list[str]:
    """Return artifact commands that have run folders."""
    names = ["order", "match-products", "export-products", "remove-cart"]
    return [name for name in names if (ARTIFACTS_DIR / name).is_dir()]


def command_profile_options(command: str) -> list[str]:
    """Return profile folders for one artifact command."""
    root = ARTIFACTS_DIR / command
    profiles = sorted(path.name for path in root.iterdir() if path.is_dir())
    return profiles or ["wardany"]


def command_run_options(command: str, profile_key: str) -> list[str]:
    """Return run folders for one command/profile pair."""
    root = ARTIFACTS_DIR / command / profile_key
    runs = sorted((path.name for path in root.iterdir() if path.is_dir()), reverse=True)
    return runs or [""]


def render_run_dir_results(command: str, profile_key: str, run_dir: Path) -> None:
    """Render files and summaries from one command run directory."""
    st.caption(f"{command} / {profile_key} / {run_dir.name}")
    summary_rows = run_summary_rows(run_dir)
    if summary_rows:
        render_timing_metrics(summary_rows)
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    render_run_table(run_dir, "Manual Review", "manual_review_*.csv")
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


def render_run_table(run_dir: Path, title: str, pattern: str) -> None:
    """Render an optional run-scoped CSV table."""
    paths = sorted(run_dir.glob(pattern))
    if not paths:
        return
    rows = load_csv_rows(paths[0])
    if rows:
        st.subheader(title)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_recent_run_files(run_dir: Path) -> None:
    """Render recent files from one run directory."""
    files = sorted(run_dir.glob("*"), key=lambda path: path.stat().st_mtime, reverse=True)
    rows = [
        {"name": path.name, "size_kb": round(path.stat().st_size / 1024, 1)}
        for path in files[:30]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
