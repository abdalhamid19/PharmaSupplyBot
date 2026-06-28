"""Table rendering functions for results tab."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.order_ai_artifacts import summarize_order_ai_rows
from .streamlit_shared import load_csv_rows
from .streamlit_timing_view import render_timing_metrics


def render_run_table(run_dir: Path, title: str, pattern: str) -> None:
    """Render an optional run-scoped CSV table."""
    paths = sorted(run_dir.glob(pattern))
    if not paths:
        return
    rows = load_csv_rows(paths[0])
    if rows:
        st.subheader(title)
        if title == "Order AI Trace":
            render_order_ai_trace_summary(rows)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_order_ai_trace_summary(rows: list[dict[str, str]]) -> None:
    """Render compact AI/API trace grouping before the full table."""
    summary = summarize_order_ai_rows(rows)
    if summary:
        st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)


def render_recent_run_files(run_dir: Path) -> None:
    """Render recent files from one run directory."""
    files = sorted(run_dir.glob("*"), key=lambda path: path.stat().st_mtime, reverse=True)
    rows = [
        {"name": path.name, "size_kb": round(path.stat().st_size / 1024, 1)}
        for path in files[:30]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_recent_artifact_files(profile_key: str) -> None:
    """Render the recent artifact files table for one profile."""
    from .streamlit_shared import ARTIFACTS_DIR
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
