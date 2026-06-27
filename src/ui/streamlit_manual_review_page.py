"""Dedicated Manual Review tab for evaluating top candidate matches."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from .streamlit_manual_review_page_candidates import render_run_candidates
from .streamlit_manual_review_page_saved import render_saved_decisions
from .streamlit_shared import ARTIFACTS_DIR, load_csv_rows
from .streamlit_manual_review import render_manual_review_editor
from .streamlit_remove_cart import render_running_remove_cart_controls
from .streamlit_manual_review_search import render_running_search_controls


def render_manual_review_tab() -> None:
    """Render the full manual review workflow with candidate options."""
    st.title("Manual Review")
    st.markdown("Select an artifact run to evaluate AI matches and correct them.")
    
    if render_running_remove_cart_controls("manual_review") or render_running_search_controls():
        return

    runs = _available_runs_with_candidates()
    if not runs:
        st.info("No matching runs with manual review candidates found.")
        render_saved_decisions()
        return

    selected_run = st.selectbox("Select Run", runs, format_func=lambda r: f"{r.parent.parent.name} / {r.parent.name} / {r.name}")
    if selected_run:
        _render_selected_run(selected_run)
        render_saved_decisions()


def _render_selected_run(selected_run):
    """Render the selected run's manual review."""
    paths = list(selected_run.glob("manual_review_*.csv"))
    if paths:
        rows = load_csv_rows(paths[0])
        if rows:
            render_manual_review_editor(rows, selected_run)
            st.divider()
    render_run_candidates(selected_run)


def _available_runs_with_candidates() -> list[Path]:
    runs = []
    if not ARTIFACTS_DIR.exists():
        return runs
    for c_dir in filter(lambda p: p.is_dir(), ARTIFACTS_DIR.iterdir()):
        for p_dir in filter(lambda p: p.is_dir(), c_dir.iterdir()):
            for r_dir in filter(lambda p: p.is_dir(), p_dir.iterdir()):
                # List any run that has been fully processed (has order_item_summary)
                if list(r_dir.glob("order_item_summary_*.csv")):
                    runs.append(r_dir)
    return sorted(runs, reverse=True)
