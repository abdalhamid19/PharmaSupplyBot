"""Action handling functions for saved decisions page."""

from __future__ import annotations

import streamlit as st

from .streamlit_manual_review_db import manual_review_store_or_stop
from .streamlit_manual_review_search import start_corrected_item_search
from .streamlit_shared import ARTIFACTS_DIR
from .streamlit_manual_review_page_saved_approval import (
    _handle_approval_conversion,
    _render_conversion_button,
    _convert_to_approved,
)


def _render_saved_actions(display_df, decisions):
    """Render editor, actions, and download/search buttons."""
    _show_saved_instructions()
    edited_df = _render_saved_editor(display_df)
    _handle_saved_modifications(display_df, edited_df)
    _render_download_and_search(display_df, decisions)


def _show_saved_instructions():
    """Show instruction messages for saved decisions."""
    st.info(
        "💡 You can delete rows directly from the table below. Select a row "
        "and press Delete (or click the trash icon) to revoke the decision "
        "and return the item to AI matching."
    )
    st.info(
        "💡 You can check the 'تحديد (Select)' box to select 'auto_matched' "
        "items and convert them to 'approved_match' using the button below."
    )


def _render_saved_editor(display_df):
    """Render the data editor for saved decisions."""
    return st.data_editor(
        display_df, use_container_width=True, hide_index=True,
        num_rows="dynamic", key="saved_decisions_editor"
    )


def _handle_saved_modifications(display_df, edited_df):
    """Handle approval conversion and deletion."""
    store = manual_review_store_or_stop()
    _handle_approval_conversion(edited_df, store)
    _handle_deletion(display_df, edited_df, store)


def _render_download_and_search(display_df, decisions):
    """Render download button and search trigger."""
    download_df = display_df.drop(columns=["تحديد (Select)"], errors="ignore")
    csv_data = download_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Corrected Items (CSV)", data=csv_data,
        file_name="saved_corrected_items.csv", mime="text/csv"
    )
    
    if st.button("Search Corrected Items (Run Match-Only)"):
        _trigger_search(decisions)


def _trigger_search(decisions: list) -> None:
    valid_status = ("needs_correction", "approved_match", "auto_matched")
    fake_rows = [
        {"item_code": d.item_code, "item_name": d.item_name}
        for d in decisions if d.manual_decision in valid_status
    ]
    dummy_run_dir = ARTIFACTS_DIR / "match-products" / "manual_research"
    dummy_run_dir.mkdir(parents=True, exist_ok=True)
    start_corrected_item_search(fake_rows, dummy_run_dir, st)
    st.success("Started corrected item search!")


def _handle_deletion(display_df, edited_df, store):
    """Handle deletion of selected items."""
    if len(edited_df) >= len(display_df):
        return
        
    deleted_pairs = deleted_identity_pairs(display_df, edited_df)
    if deleted_pairs:
        if st.button("🗑️ Confirm Deletion of Selected Items"):
            for code, name in deleted_pairs:
                store.delete(code, name)
            st.success(
                f"Successfully deleted {len(deleted_pairs)} items from saved corrections!"
            )
            st.rerun()


def deleted_identity_pairs(original_df, edited_df) -> list[tuple[str, str]]:
    """Return (item_code, item_name) pairs removed from the edited table.

    Matching on the full identity pair prevents deleting unrelated corrections
    that happen to share the same item_code.
    """
    original = set(zip(original_df["item_code"], original_df["item_name"]))
    edited = set(zip(edited_df["item_code"], edited_df["item_name"]))
    return sorted(original - edited)


__all__ = [
    "_render_saved_actions",
    "_show_saved_instructions",
    "_render_saved_editor",
    "_handle_saved_modifications",
    "_render_download_and_search",
    "_handle_deletion",
    "deleted_identity_pairs",
    "_trigger_search",
]
