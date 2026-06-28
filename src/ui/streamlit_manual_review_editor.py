"""Editor UI for manual review in Streamlit."""

import pandas as pd
import streamlit as st

from .streamlit_manual_review_db import manual_review_store_or_stop
from .streamlit_manual_review_rows import editable_manual_review_rows
from .streamlit_manual_review_pagination import _show_stats, _paginate_rows, _select_columns


def render_manual_review_editor(rows: list[dict[str, str]], run_dir) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    
    store = manual_review_store_or_stop()
    editable_rows = _load_editable_rows(rows, store, run_dir)
    edited_records = _render_editor_ui(editable_rows)
    _update_cache_after_edit(editable_rows, edited_records, run_dir)
    return edited_records


def _render_editor_ui(editable_rows: list[dict]) -> list[dict]:
    """Render stats, pagination, and data editor."""
    _show_stats(editable_rows)
    visible_rows = _paginate_rows(editable_rows)
    selected_columns = _select_columns(visible_rows)
    edited = st.data_editor(
        pd.DataFrame(visible_rows), 
        use_container_width=True,
        column_order=selected_columns if selected_columns else None
    )
    return edited.to_dict("records")


def _load_editable_rows(rows, store, run_dir):
    """Load and cache editable rows."""
    cache_key = f"manual_review_cache_{run_dir.name}"
    if cache_key not in st.session_state:
        with st.spinner("Loading saved decisions..."):
            editable_rows = editable_manual_review_rows(rows, store)
            st.session_state[cache_key] = editable_rows
    else:
        editable_rows = st.session_state[cache_key]
    return editable_rows


def _update_cache_after_edit(editable_rows, edited_records, run_dir):
    """Update cache with edited records without full rerun."""
    cache_key = f"manual_review_cache_{run_dir.name}"
    if cache_key in st.session_state:
        items_per_page = 50
        total_pages = max(1, (len(editable_rows) + items_per_page - 1) // items_per_page)
        if total_pages > 1:
            page_num = st.session_state.get("manual_review_page", 1)
            start_idx = (page_num - 1) * items_per_page
            for i, record in enumerate(edited_records):
                st.session_state[cache_key][start_idx + i] = record
        else:
            st.session_state[cache_key] = edited_records
