"""Pagination and column selection for manual review in Streamlit."""

import streamlit as st


def _show_stats(editable_rows):
    """Show item statistics."""
    remaining_count = sum(
        1 for row in editable_rows
        if not row.get("approved_match") and not row.get("not_matching")
    )
    total_count = len(editable_rows)
    corrected_count = total_count - remaining_count
    
    st.caption(
        f"📊 Total: {total_count} items | ✅ Corrected: {corrected_count} | "
        f"⏳ Remaining: {remaining_count}"
    )


def _paginate_rows(editable_rows):
    """Paginate rows and return visible subset."""
    items_per_page = 50
    total_pages = max(1, (len(editable_rows) + items_per_page - 1) // items_per_page)
    
    if total_pages > 1:
        return _paginate_multi_page(editable_rows, total_pages, items_per_page)
    return editable_rows


def _paginate_multi_page(editable_rows, total_pages, items_per_page):
    """Handle multi-page pagination."""
    page = st.number_input(
        f"Page (1-{total_pages})",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.get("manual_review_page", 1),
        key="manual_review_page_input"
    )
    st.session_state["manual_review_page"] = page
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(editable_rows))
    visible_rows = editable_rows[start_idx:end_idx]
    st.caption(f"Showing {start_idx + 1}-{end_idx} of {len(editable_rows)}")
    return visible_rows


def _select_columns(visible_rows):
    """Allow column selection for display."""
    if not visible_rows:
        return None
        
    all_cols = list(visible_rows[0].keys())
    default_cols = _default_manual_review_columns()
    default_cols = [c for c in default_cols if c in all_cols]
    sorted_options = _sorted_column_options(default_cols, all_cols)
            
    return st.multiselect(
        "اختر الأعمدة المراد عرضها (Select Columns to Display):",
        options=sorted_options,
        default=default_cols,
        key="manual_review_columns_multiselect"
    )


def _default_manual_review_columns():
    """Return default columns for manual review display."""
    return [
        "item_code", "item_name", "matched_product_name_en", "item_qty", "status",
        "approved_match", "not_matching", 
        "correct_store_product_id", "correct_product_name", "correct_query",
        "reason", "matched_query"
    ]


def _sorted_column_options(default_cols, all_cols):
    """Sort column options with defaults first."""
    sorted_options = list(default_cols)
    for c in all_cols:
        if c not in sorted_options:
            sorted_options.append(c)
    return sorted_options
