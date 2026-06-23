"""Candidate rendering for the Manual Review tab."""

from __future__ import annotations

from pathlib import Path
import streamlit as st

from ..core.manual_review_candidate_store import load_review_candidates
from ..core.manual_review_candidates import ReviewCandidateOption
from ..core.manual_review_store import ManualReviewStore
from ..core.utils.excel import Item
from .streamlit_manual_review_db import manual_review_store_or_stop
from .streamlit_manual_review_page_form import render_selection_form


def render_run_candidates(run_dir: Path) -> None:
    """Render the evaluation cards for the selected run."""
    st.subheader(f"Candidates from run: {run_dir.name}")
    candidates_dict = load_review_candidates(run_dir)
    
    if not candidates_dict:
        st.success("🎉 All items in this run were processed automatically! No manual review is required.")
        return

    store = manual_review_store_or_stop()
    hide_completed = st.checkbox("Hide completed items", value=True)
    
    # ⚡ Get current page from manual review pagination
    current_page = st.session_state.get("manual_review_page", 1)
    items_per_page = 50
    
    # Convert to list for pagination
    all_items = list(candidates_dict.items())
    
    # Filter completed if needed
    if hide_completed:
        filtered_items = []
        for item_key, options in all_items:
            parts = item_key.split("::", 1)
            item_code = parts[0].upper()
            item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
            if not store.lookup(item_code, item_name):
                filtered_items.append((item_key, options))
        display_items = filtered_items
    else:
        display_items = all_items
    
    # Show stats
    total_candidates = len(display_items)
    st.caption(f"📊 Candidates: {total_candidates} items")
    
    # Apply pagination - show candidates for current page only
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_candidates)
    page_items = display_items[start_idx:end_idx]
    
    if total_candidates > items_per_page:
        st.caption(f"Showing candidates {start_idx + 1}-{end_idx} (matching page {current_page})")
    
    for item_key, options in page_items:
        parts = item_key.split("::", 1)
        item_code = parts[0].upper()
        item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
        item = Item(code=item_code, name=item_name, qty="1")
        _render_item_card(item_key, item, options, run_dir, store)


def _render_item_card(
    item_key: str, item: Item, options: list[ReviewCandidateOption], run_dir: Path, store: ManualReviewStore
) -> None:
    with st.expander(f"Review: {item.name} ({item.code})", expanded=True):
        st.markdown(f"**Requested Item:** {item.name}")
        render_selection_form(item, options, run_dir, store, item_key)
