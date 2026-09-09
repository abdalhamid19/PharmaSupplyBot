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
    _render_source_history(store)
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
        "item_code", "item_name", "run_date", "decision", "manual_decision",
        "matching_source", "matching_source_label",
        "supplier_scope_key", "last_rebind_status",
        "correct_product_name", "correct_product_name_ar"
    ]
    default_columns = [col for col in default_columns if col in all_columns]
    return st.multiselect(
        "Select columns to display and download:",
        options=all_columns,
        default=default_columns,
        key="saved_decisions_columns_v2",
    )


def _build_editor_columns(selected_columns):
    """Build editor columns with identity columns first."""
    # Supplier scope is part of the persistent identity.  Keep it in the
    # editor even when the user customises the visible business columns so a
    # deletion or approval can never fall back to item-only behaviour.
    identity_columns = [
        "item_code", "item_name", "matching_source", "matching_source_label",
        "excel_target_key",
    ]
    return identity_columns + [c for c in selected_columns if c not in identity_columns]


def _prepare_display_df(df, editor_columns, selected_columns):
    """Prepare and sort display dataframe."""
    sort_col, is_ascending = _get_sort_preferences(selected_columns)
    display_df = df[editor_columns].copy()
    display_df.insert(0, "تحديد (Select)", False)
    if sort_col:
        # Keep the store's newest-first order for rows sharing the same run
        # timestamp (for example, decisions saved in one batch).
        sort_key = None
        if sort_col == "run_date":
            # Legacy imports use values such as ``csv_import`` instead of a
            # timestamp.  Treat those values as unknown dates so they stay
            # below real timestamped runs when sorting newest first.
            sort_key = lambda values: pd.to_datetime(
                values.astype("string"),
                format="%Y%m%d_%H%M",
                errors="coerce",
            )
        display_df = display_df.sort_values(
            by=sort_col,
            ascending=is_ascending,
            kind="stable",
            key=sort_key,
            na_position="last",
        )
    return display_df


def _default_sort_preferences(selected_columns):
    """Return the default sort column and direction for saved corrections."""
    if "run_date" in selected_columns:
        return "run_date", False
    if "item_name" in selected_columns:
        return "item_name", True
    if selected_columns:
        return selected_columns[0], True
    return None, True


def _get_sort_preferences(selected_columns):
    """Get user sort column and order preferences."""
    col_sort, col_order = st.columns(2)
    default_sort_col, default_ascending = _default_sort_preferences(selected_columns)
    with col_sort:
        default_idx = (
            selected_columns.index(default_sort_col)
            if default_sort_col in selected_columns else 0
        )
        sort_col = st.selectbox(
            "ترتيب حسب (Sort By):",
            options=selected_columns,
            index=default_idx,
            key="saved_decisions_sort_column_v2",
        )
    with col_order:
        sort_asc = st.radio(
            "ترتيب (Order):",
            options=["تصاعدي (Ascending)", "تنازلي (Descending)"],
            index=0 if default_ascending else 1,
            horizontal=True,
            key="saved_decisions_sort_order_v2",
        )
    is_ascending = sort_asc == "تصاعدي (Ascending)"
    return sort_col, is_ascending


def _decision_row(d) -> dict:
    """Return a backward-compatible, provenance-rich display row."""
    target_key = getattr(d, "excel_target_key", "")
    source = getattr(d, "matching_source", "") or getattr(d, "source_kind", "")
    if not source and target_key:
        # Decisions written before the explicit source migration can still be
        # identified safely from their target scope.
        source = "excel_target"
    return {
        "item_code": d.item_code,
        "item_name": d.item_name,
        "run_date": d.run_id,
        "decision": d.manual_decision,
        "manual_decision": d.manual_decision,
        "matching_source": source,
        "matching_source_label": getattr(d, "matching_source_label", "") or "",
        "identity_evidence_kind": getattr(d, "identity_evidence_kind", "") or "",
        "identity_evidence": getattr(d, "identity_evidence", "") or "",
        "correct_store_product_id": d.correct_store_product_id,
        "correct_product_name": getattr(d, "correct_product_name", ""),
        "correct_product_name_ar": getattr(d, "correct_product_name_ar", ""),
        "correct_query": d.correct_query,
        "run_id": d.run_id,
        "excel_target_key": target_key,
        "excel_target_source_file": getattr(d, "excel_target_source_file", "") or "",
        "supplier_scope_key": getattr(d, "supplier_scope_key", "") or "",
        "last_rebind_status": getattr(d, "last_rebind_status", "") or "",
        "approved": d.approved,
    }


# ============ Action Handling ============

def _render_saved_actions(display_df, decisions):
    """Render editor, actions, and download/search buttons."""
    _show_saved_instructions()
    edited_df = _render_saved_editor(display_df)
    _handle_saved_modifications(display_df, edited_df)
    _render_download_and_search(display_df, decisions)


def _render_source_history(store) -> None:
    """Show catalog files previously observed for logical supplier decisions."""
    history = store.list_all_source_history()
    if not history:
        return
    with st.expander("Supplier catalog history", expanded=False):
        st.dataframe(
            pd.DataFrame([dataclasses.asdict(row) for row in history]),
            hide_index=True,
            width="stretch",
        )


def _show_saved_instructions():
    """Show instruction messages for saved decisions."""
    st.info(
        "💡 You can delete rows directly from the table below. Select a row "
        "and press Delete (or click the trash icon) to revoke the decision "
        "and return the item to local matching."
    )
    st.info(
        "💡 You can check the 'تحديد (Select)' box to select 'auto_matched' "
        "items and convert them to 'approved_match' using the button below."
    )


def _render_saved_editor(display_df):
    """Render the data editor for saved decisions."""
    return st.data_editor(
        display_df,
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        key="saved_decisions_editor_v2",
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
    dummy_run_dir = ARTIFACTS_DIR / "order" / "manual_research"
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
            for code, name, source, source_label, target_key in deleted_pairs:
                kwargs = {"matching_source": source}
                if source.replace("_", "-") == "excel-target" and target_key:
                    kwargs["excel_target_key"] = target_key
                else:
                    kwargs["matching_source_label"] = source_label
                store.delete(code, name, **kwargs)
            st.success(
                f"Successfully deleted {len(deleted_pairs)} items from saved corrections!"
            )
            st.rerun()


def deleted_identity_pairs(original_df, edited_df) -> list[tuple[str, str, str, str, str]]:
    """Return exact item-and-supplier identities removed from the table."""
    columns = [
        "item_code", "item_name", "matching_source", "matching_source_label",
        "excel_target_key",
    ]
    original = set(original_df.reindex(columns=columns, fill_value="").itertuples(index=False, name=None))
    edited = set(edited_df.reindex(columns=columns, fill_value="").itertuples(index=False, name=None))
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
        source = str(row.get("matching_source", "") or "")
        target_key = str(row.get("excel_target_key", "") or "")
        lookup_kwargs = {"matching_source": source}
        if source.replace("_", "-") == "excel-target" and target_key:
            lookup_kwargs["excel_target_key"] = target_key
        else:
            lookup_kwargs["matching_source_label"] = str(
                row.get("matching_source_label", "") or ""
            )
        decision_obj = store.lookup(
            str(row["item_code"]), str(row["item_name"]), **lookup_kwargs
        )
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
