"""Overview tab rendering for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .streamlit_shared import (
    ARTIFACTS_DIR,
    ORDER_ITEMS_DIR,
    PREVENTED_ITEMS_DIR,
    load_csv_rows,
)


def render_overview(app_config) -> None:
    """Render high-level project status and local environment details."""
    input_files = sorted(ORDER_ITEMS_DIR.glob("*.xlsx")) if ORDER_ITEMS_DIR.exists() else []
    prevented_files = (
        sorted(PREVENTED_ITEMS_DIR.glob("*.xlsx")) if PREVENTED_ITEMS_DIR.exists() else []
    )
    summary_path = ARTIFACTS_DIR / "wardany" / "order_result_summary.csv"
    summary_rows = load_csv_rows(summary_path)
    render_overview_metrics(app_config, input_files, prevented_files, summary_rows)
    render_profile_table(app_config.profiles)
    render_input_files_table(input_files, prevented_files)
    render_latest_summary_rows(summary_rows)


def render_overview_metrics(
    app_config,
    input_files: list[Path],
    prevented_files: list[Path],
    summary_rows: list[dict[str, str]],
) -> None:
    """Render top-line project metrics for the overview tab."""
    metrics = st.columns(4)
    metrics[0].metric("Profiles", len(app_config.profiles))
    metrics[1].metric("Order Excel Files", len(input_files))
    metrics[2].metric("Recent Summary Rows", len(summary_rows))
    submit_order = "On" if app_config.runtime.submit_order else "Off"
    metrics[3].metric("Submit Order", submit_order)


def render_profile_table(profiles) -> None:
    """Render the configured profiles table."""
    st.subheader("Profiles")
    rows = []
    for profile_key, profile in profiles.items():
        state_path = Path("state") / f"{profile_key}.json"
        rows.append(_profile_row(profile_key, profile.display_name, state_path))
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _profile_row(profile_key: str, display_name: str, state_path: Path) -> dict[str, object]:
    """Return one profile row for the overview table."""
    return {
        "profile": profile_key,
        "display_name": display_name,
        "state_file": state_path.name,
        "state_exists": state_path.exists(),
    }


def render_input_files_table(input_files: list[Path], prevented_files: list[Path]) -> None:
    """Render the available Excel files table."""
    st.subheader("Available Order Excel Files")
    rows = file_table_rows(input_files, "order_items")
    if not rows:
        st.info("No order Excel files found under `input/order_items/`.")
    else:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("Available Prevented Excel Files")
    prevented_rows = file_table_rows(prevented_files, "prevented_items")
    if not prevented_rows:
        st.info("No prevented-items Excel files found under `input/prevented_items/`.")
        return
    st.dataframe(pd.DataFrame(prevented_rows), use_container_width=True, hide_index=True)


def file_table_rows(files: list[Path], category: str) -> list[dict[str, object]]:
    """Return display rows for one local Excel-file category."""
    return [
        {
            "file": str(file),
            "category": category,
            "size_kb": round(file.stat().st_size / 1024, 1),
        }
        for file in files
    ]


def render_latest_summary_rows(summary_rows: list[dict[str, str]]) -> None:
    """Render the latest summary rows block when data exists."""
    if not summary_rows:
        return
    st.subheader("Latest Order Summary Rows")
    st.dataframe(pd.DataFrame(summary_rows[-10:]), use_container_width=True, hide_index=True)
