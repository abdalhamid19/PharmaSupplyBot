"""Saved decisions rendering for the Manual Review tab."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..core.manual_review_store import ManualReviewStore
from .streamlit_manual_review_search import start_corrected_item_search
from .streamlit_shared import ARTIFACTS_DIR


def render_saved_decisions() -> None:
    """Render a table of previously corrected items and allow re-searching."""
    st.divider()
    st.subheader("Saved Corrections (Manual Review Store)")
    decisions = ManualReviewStore().list_decisions()
    
    if not decisions:
        st.info("No saved decisions found.")
        return
        
    df = pd.DataFrame([_decision_row(d) for d in decisions])
    
    all_columns = list(df.columns)
    default_columns = ["item_code", "item_name", "decision", "correct_product_name", "correct_product_name_ar"]
    # Ensure default columns exist in the DataFrame
    default_columns = [col for col in default_columns if col in all_columns]
    
    selected_columns = st.multiselect(
        "Select columns to display and download:",
        options=all_columns,
        default=default_columns
    )
    
    if not selected_columns:
        st.warning("Please select at least one column.")
        return
    col_sort, col_order = st.columns(2)
    with col_sort:
        sort_col = st.selectbox("ترتيب حسب (Sort By):", options=selected_columns, index=selected_columns.index("item_name") if "item_name" in selected_columns else 0)
    with col_order:
        sort_asc = st.radio("ترتيب (Order):", options=["تصاعدي (Ascending)", "تنازلي (Descending)"], horizontal=True)

    display_df = df[selected_columns]
    
    if sort_col:
        is_ascending = sort_asc == "تصاعدي (Ascending)"
        display_df = display_df.sort_values(by=sort_col, ascending=is_ascending)
    st.info("💡 You can delete rows directly from the table below. Select a row and press Delete (or click the trash icon) to revoke the decision and return the item to AI matching.")
    edited_df = st.data_editor(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        num_rows="dynamic",
        key="saved_decisions_editor"
    )
    
    if len(edited_df) < len(display_df):
        original_codes = set(display_df["item_code"])
        edited_codes = set(edited_df["item_code"])
        deleted_codes = original_codes - edited_codes
        
        if deleted_codes:
            if st.button("🗑️ Confirm Deletion of Selected Items"):
                store = ManualReviewStore()
                deleted_count = 0
                for d in decisions:
                    if d.item_code in deleted_codes:
                        store.delete(d.item_code, d.item_name)
                        deleted_count += 1
                st.success(f"Successfully deleted {deleted_count} items from saved corrections!")
                st.rerun()
    
    csv_data = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Download Corrected Items (CSV)",
        data=csv_data,
        file_name="saved_corrected_items.csv",
        mime="text/csv",
    )
    
    if st.button("Search Corrected Items (Run Match-Only)"):
        _trigger_search(decisions)


def _decision_row(d) -> dict:
    return {
        "item_code": d.item_code,
        "item_name": d.item_name,
        "decision": d.manual_decision,
        "correct_store_product_id": d.correct_store_product_id,
        "correct_product_name": getattr(d, "correct_product_name", ""),
        "correct_product_name_ar": getattr(d, "correct_product_name_ar", ""),
        "correct_query": d.correct_query,
        "run_id": d.run_id,
        "approved": d.approved,
    }


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
