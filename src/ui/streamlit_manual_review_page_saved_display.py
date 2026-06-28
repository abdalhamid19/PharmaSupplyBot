"""Display preparation functions for saved decisions page."""

from __future__ import annotations

import pandas as pd
import streamlit as st


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
