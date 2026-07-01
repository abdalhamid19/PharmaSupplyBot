"""Saved decisions rendering for the Manual Review tab."""

from __future__ import annotations

import dataclasses
import pandas as pd
import streamlit as st

from ...core.manual_review.manual_review_store import ManualReviewStore
from .streamlit_manual_review import manual_review_store_or_stop, start_corrected_item_search
from ..streamlit_shared import ARTIFACTS_DIR


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


# ============ Display Preparation ============

def _prepare_saved_decisions_display(decisions, store):
    """Prepare and validate display DataFrame."""
    df = pd.DataFrame([_decision_row(d) for d in decisions])
    selected_columns = _select_saved_columns(df)
    if not selected_columns:
        st.warning("Please select at least one column.")
        return None
    editor_columns = _build_editor_columns(selected_columns)
    return _prepare_display_df(df, editor_columns, selected_columns)


def _select_saved_columns(df):
    """Select columns to display."""
    all_columns = list(df.columns)
    default_columns = [
        "item_code", "item_name", "run_date", "decision",
        "correct_product_name", "correct_product_name_ar"
    ]
    default_columns = [col for col in default_columns if col in all_columns]
    return st.multiselect(
        "Select columns to display and download:",
        options=all_columns, default=default_columns
    )


def _build_editor_columns(selected_columns):
    """Build editor columns with identity columns first."""
    identity_columns = ["item_code", "item_name"]
    return identity_columns + [c for c in selected_columns if c not in identity_columns]


def _prepare_display_df(df, editor_columns, selected_columns):
    """Prepare and sort display dataframe."""
    sort_col, is_ascending = _get_sort_preferences(selected_columns)
    display_df = df[editor_columns].copy()
    display_df.insert(0, "تحديد (Select)", False)
    if sort_col:
        display_df = display_df.sort_values(by=sort_col, ascending=is_ascending)
    return display_df


def _get_sort_preferences(selected_columns):
    """Get user sort column and order preferences."""
    col_sort, col_order = st.columns(2)
    with col_sort:
        default_idx = (
            selected_columns.index("item_name")
            if "item_name" in selected_columns else 0
        )
        sort_col = st.selectbox(
            "ترتيب حسب (Sort By):", options=selected_columns, index=default_idx
        )
    with col_order:
        sort_asc = st.radio(
            "ترتيب (Order):",
            options=["تصاعدي (Ascending)", "تنازلي (Descending)"],
            horizontal=True
        )
    is_ascending = sort_asc == "تصاعدي (Ascending)"
    return sort_col, is_ascending


def _decision_row(d) -> dict:
    return {
        "item_code": d.item_code,
        "item_name": d.item_name,
        "run_date": d.run_id,
        "decision": d.manual_decision,
        "correct_store_product_id": d.correct_store_product_id,
        "correct_product_name": getattr(d, "correct_product_name", ""),
        "correct_product_name_ar": getattr(d, "correct_product_name_ar", ""),
        "correct_query": d.correct_query,
        "run_id": d.run_id,
        "approved": d.approved,
    }


# ============ Action Handling ============

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
    """Return (item_code, item_name) pairs removed from the edited table."""
    original = set(zip(original_df["item_code"], original_df["item_name"]))
    edited = set(zip(edited_df["item_code"], edited_df["item_name"]))
    return sorted(original - edited)


# ============ Approval Conversion ============

def _handle_approval_conversion(edited_df, store):
    """Handle conversion from auto_matched to approved_match."""
    selected_auto_matched = edited_df[
        (edited_df["تحديد (Select)"] == True) &
        (edited_df["decision"] == "auto_matched")
    ]
    if selected_auto_matched.empty:
        return
    _render_conversion_button(selected_auto_matched, store)


def _render_conversion_button(selected_auto_matched, store):
    """Render conversion button and handle conversion."""
    button_label = (
        f"✔️ تحويل {len(selected_auto_matched)} صنف محدد من "
        f"auto_matched إلى approved_match"
    )
    if st.button(button_label, type="primary"):
        _convert_to_approved(selected_auto_matched, store)


def _convert_to_approved(selected_auto_matched, store):
    """Convert selected auto_matched items to approved_match."""
    for _, row in selected_auto_matched.iterrows():
        decision_obj = store.lookup(str(row["item_code"]), str(row["item_name"]))
        if decision_obj and decision_obj.manual_decision == "auto_matched":
            new_decision = dataclasses.replace(
                decision_obj, manual_decision="approved_match"
            )
            store.upsert(new_decision)
    st.success(
        f"Successfully converted {len(selected_auto_matched)} items to approved_match!"
    )
    st.rerun()


__all__ = [
    "render_saved_decisions",
    "deleted_identity_pairs",
    "_decision_row",
]
