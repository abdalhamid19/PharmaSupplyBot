"""Dedicated Manual Review tab for evaluating top candidate matches."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from .streamlit_manual_review_page_candidates import render_run_candidates
from .streamlit_manual_review_page_saved import render_saved_decisions
from .streamlit_shared import ARTIFACTS_DIR


def render_manual_review_tab() -> None:
    """Render the full manual review workflow with candidate options."""
    st.title("Manual Review")
    st.markdown("Select an artifact run to evaluate AI matches and correct them.")

    runs = _available_runs_with_candidates()
    if not runs:
        st.info("No matching runs with manual review candidates found.")
        render_saved_decisions()
        return

    selected_run = st.selectbox(
        "Select Run", runs, 
        format_func=lambda r: f"{r.parent.parent.name} / {r.parent.name} / {r.name}"
    )
    if selected_run:
        render_run_candidates(selected_run)
        render_saved_decisions()


def _available_runs_with_candidates() -> list[Path]:
    runs = []
    if not ARTIFACTS_DIR.exists():
        return runs
    for c_dir in filter(lambda p: p.is_dir(), ARTIFACTS_DIR.iterdir()):
        for p_dir in filter(lambda p: p.is_dir(), c_dir.iterdir()):
            for r_dir in filter(lambda p: p.is_dir(), p_dir.iterdir()):
                if list(r_dir.glob("manual_review_candidates_*.jsonl")):
                    runs.append(r_dir)
    return sorted(runs, reverse=True)
