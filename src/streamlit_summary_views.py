"""Summary table views for the Streamlit GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


def render_summary_views(
    profile_key: str,
    summary_csv: Path,
    csv_rows: list[dict[str, str]],
    summary_xlsx: Path,
    xlsx_rows: list[dict[str, str]],
) -> None:
    """Render order summary data from both CSV and XLSX artifacts when available."""
    st.markdown(f"**Summary profile:** `{profile_key}`")
    render_summary_captions(summary_csv, summary_xlsx)
    maybe_warn_stale_xlsx(summary_csv, summary_xlsx)
    render_summary_tabs(csv_rows, xlsx_rows)


def render_summary_captions(summary_csv: Path, summary_xlsx: Path) -> None:
    """Render the CSV/XLSX summary file captions."""
    csv_col, xlsx_col = st.columns(2)
    with csv_col:
        st.caption(f"CSV: `{summary_csv}`")
    with xlsx_col:
        suffix = "" if summary_xlsx.exists() else " (missing)"
        st.caption(f"XLSX: `{summary_xlsx}`{suffix}")


def maybe_warn_stale_xlsx(summary_csv: Path, summary_xlsx: Path) -> None:
    """Warn when the XLSX summary is older than the CSV summary."""
    if not summary_csv.exists() or not summary_xlsx.exists():
        return
    if summary_xlsx.stat().st_mtime < summary_csv.stat().st_mtime:
        st.warning("`order_result_summary.xlsx` is older than the CSV and may miss the latest run.")


def render_summary_tabs(csv_rows: list[dict[str, str]], xlsx_rows: list[dict[str, str]]) -> None:
    """Render the CSV/XLSX summary tabs."""
    csv_tab, xlsx_tab = st.tabs(["CSV", "XLSX"])
    with csv_tab:
        render_summary_table(csv_rows, "CSV summary is missing or empty.")
    with xlsx_tab:
        render_summary_table(xlsx_rows, "XLSX summary is missing or empty.")


def render_summary_table(rows: list[dict[str, str]], empty_message: str) -> None:
    """Render one summary table or an empty-state message."""
    if not rows:
        st.info(empty_message)
        return
    st.dataframe(pd.DataFrame(rows[-100:]), use_container_width=True, hide_index=True)
