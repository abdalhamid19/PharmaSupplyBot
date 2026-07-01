"""Timing report views for the Streamlit GUI."""

from __future__ import annotations

import streamlit as st

from .streamlit_timing import (
    average_value,
    elapsed_seconds_values,
    match_elapsed_seconds_values,
    timing_breakdown,
    top_slowest_rows,
)


def render_timing_metrics(rows: list[dict[str, str]]) -> None:
    """Render elapsed-time metrics from populated summary rows."""
    elapsed_values = elapsed_seconds_values(rows)
    if not elapsed_values:
        st.info("No populated `elapsed_seconds` rows found.")
        return
    render_timing_header_metrics(rows, elapsed_values)
    left, right = st.columns(2)
    with left:
        st.markdown("**Timing summary**")
        st.dataframe(timing_breakdown(rows), use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Top slowest items**")
        st.dataframe(top_slowest_rows(rows), use_container_width=True, hide_index=True)


def render_timing_header_metrics(rows: list[dict[str, str]], elapsed_values: list[float]) -> None:
    """Render the top-line timing metrics."""
    match_values = match_elapsed_seconds_values(rows)
    metrics = st.columns(4)
    metrics[0].metric("Rows", len(rows))
    metrics[1].metric("Average seconds", f"{average_value(elapsed_values):.2f}")
    metrics[2].metric("Min seconds", f"{min(elapsed_values):.3f}")
    metrics[3].metric("Max seconds", f"{max(elapsed_values):.3f}")
    if match_values:
        st.caption(f"Average match-only seconds: {average_value(match_values):.3f}")
