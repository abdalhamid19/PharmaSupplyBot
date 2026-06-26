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
        st.success(
            "🎉 All items in this run were processed automatically! "
            "No manual review is required."
        )
        return

    store = manual_review_store_or_stop()
    hide_completed = st.checkbox("Hide completed items", value=True)
    display_items = _filter_and_prepare_items(candidates_dict, store, hide_completed)
    page_items = _paginate_candidates(display_items)
    
    for item_key, options in page_items:
        item = _parse_item_from_key(item_key)
        _render_item_card(item_key, item, options, run_dir, store)


def _filter_and_prepare_items(candidates_dict, store, hide_completed):
    """Filter and prepare display items based on completion status."""
    all_items = list(candidates_dict.items())
    
    if not hide_completed:
        return all_items
    
    filtered_items = []
    for item_key, options in all_items:
        parts = item_key.split("::", 1)
        item_code = parts[0].upper()
        item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
        if not store.lookup(item_code, item_name):
            filtered_items.append((item_key, options))
    return filtered_items


def _paginate_candidates(display_items):
    """Apply pagination to candidates list."""
    current_page = st.session_state.get("manual_review_page", 1)
    items_per_page = 50
    total_candidates = len(display_items)
    
    st.caption(f"📊 Candidates: {total_candidates} items")
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_candidates)
    
    if total_candidates > items_per_page:
        st.caption(f"Showing candidates {start_idx + 1}-{end_idx} (matching page {current_page})")
    
    return display_items[start_idx:end_idx]


def _parse_item_from_key(item_key):
    """Parse Item object from item_key string."""
    parts = item_key.split("::", 1)
    item_code = parts[0].upper()
    item_name = parts[1].upper() if len(parts) > 1 else "Unknown"
    return Item(code=item_code, name=item_name, qty="1")


def _render_item_card(
    item_key: str,
    item: Item,
    options: list[ReviewCandidateOption],
    run_dir: Path,
    store: ManualReviewStore
) -> None:
    with st.expander(f"Review: {item.name} ({item.code})", expanded=True):
        st.markdown(f"**Requested Item:** {item.name}")
        render_selection_form(item, options, run_dir, store, item_key)
