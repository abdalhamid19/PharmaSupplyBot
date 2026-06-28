"""Saved decisions rendering for the Manual Review tab."""

from __future__ import annotations

import streamlit as st

from .streamlit_manual_review_db import manual_review_store_or_stop
from .streamlit_manual_review_search import start_corrected_item_search
from .streamlit_shared import ARTIFACTS_DIR
from .streamlit_manual_review_page_saved_display import (
    _prepare_saved_decisions_display,
    _select_saved_columns,
    _build_editor_columns,
    _prepare_display_df,
    _get_sort_preferences,
    _decision_row,
)
from .streamlit_manual_review_page_saved_actions import (
    _render_saved_actions,
    _show_saved_instructions,
    _render_saved_editor,
    _handle_saved_modifications,
    _render_download_and_search,
    _handle_deletion,
    deleted_identity_pairs,
    _trigger_search,
)
from .streamlit_manual_review_page_saved_approval import (
    _handle_approval_conversion,
    _render_conversion_button,
    _convert_to_approved,
)


def render_saved_decisions() -> None:
    """Render a table of previously corrected items and allow re-searching."""
    st.divider()
    st.subheader("Saved Corrections (Manual Review Store)")
    store = manual_review_store_or_stop()
    decisions = store.list_decisions()
    
    if not decisions:
        st.info("No saved decisions found.")
        return
    
    display_df = _prepare_saved_decisions_display(decisions, store)
    if display_df is None:
        return
    
    _render_saved_actions(display_df, decisions)


__all__ = [
    "render_saved_decisions",
    "_prepare_saved_decisions_display",
    "_select_saved_columns",
    "_build_editor_columns",
    "_prepare_display_df",
    "_get_sort_preferences",
    "_decision_row",
    "_render_saved_actions",
    "_show_saved_instructions",
    "_render_saved_editor",
    "_handle_saved_modifications",
    "_render_download_and_search",
    "_handle_deletion",
    "deleted_identity_pairs",
    "_trigger_search",
    "_handle_approval_conversion",
    "_render_conversion_button",
    "_convert_to_approved",
]
