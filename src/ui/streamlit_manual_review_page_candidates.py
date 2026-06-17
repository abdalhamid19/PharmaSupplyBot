"""Candidate rendering for the Manual Review tab."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ..core.manual_review_candidate_store import load_review_candidates
from ..core.manual_review_candidates import ReviewCandidateOption
from ..core.manual_review_store import ManualReviewStore
from ..core.utils.excel import Item
from .streamlit_manual_review_page_form import render_selection_form


def render_run_candidates(run_dir: Path) -> None:
    """Render the evaluation cards for the selected run."""
    st.subheader(f"Candidates from run: {run_dir.name}")
    candidates_dict = load_review_candidates(run_dir)
    
    if not candidates_dict:
        st.warning("Could not parse candidates from this run.")
        return

    store = ManualReviewStore()
    hide_completed = st.checkbox("Hide completed items", value=True)
    
    for item_key, options in candidates_dict.items():
        if not options:
            continue
            
        parts = item_key.split("::", 1)
        item_code = parts[0].upper()
        item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
        item = Item(code=item_code, name=item_name, qty="1")
        
        if hide_completed and store.lookup(item.code, item.name):
            continue

        _render_item_card(item_key, item, options, run_dir, store)


def _render_item_card(
    item_key: str, item: Item, options: list[ReviewCandidateOption], run_dir: Path, store: ManualReviewStore
) -> None:
    with st.expander(f"Review: {item.name} ({item.code})", expanded=True):
        st.markdown(f"**Requested Item:** {item.name}")
        render_selection_form(item, options, run_dir, store, item_key)
