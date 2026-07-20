"""Manual-review learning controls for Streamlit result runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ...core.manual_review.manual_review_corrections import _has_correction
from ...core.manual_review.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewStore,
)
from .streamlit_manual_review_cli import (
    start_not_matching_removal,
    start_corrected_item_search,
    render_running_search_controls,
)
from .streamlit_manual_review_display import (
    _default_manual_review_columns,
    _paginate_multi_page,
    _paginate_rows,
    _select_columns,
    _show_stats,
    _sorted_column_options,
)
from .streamlit_manual_review_input import (
    editable_manual_review_rows,
    manual_review_decisions_from_rows,
    save_manual_review_rows,
)


# ============ Database Helpers ============


def manual_review_store_or_stop() -> ManualReviewStore:
    """Return the local SQLite manual-review store or stop the Streamlit page."""
    try:
        return ManualReviewStore()
    except Exception as error:
        st.error(f"Manual review database is not available: {error}")
        st.info(
            "Local SQLite DB should be at state/manual_review_decisions.db "
            "(or set SQLITE_DB_PATH in .env), then restart Streamlit."
        )
        st.stop()


# ============ Editor UI ============

def render_manual_review_editor(rows: list[dict[str, str]], run_dir) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    store = manual_review_store_or_stop()
    editable_rows = _load_editable_rows(rows, store, run_dir)
    edited_records = _render_editor_ui(editable_rows)
    _update_cache_after_edit(editable_rows, edited_records, run_dir)
    _render_action_sections(edited_records, run_dir)
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


# ============ Persistence Logic ============

def _render_action_sections(edited_records, run_dir):
    """Render all action sections (save, remove, search)."""
    _render_save_section(edited_records, run_dir)
    _render_remove_not_matching_section(edited_records, run_dir)
    _render_search_corrected_section(edited_records, run_dir)


def _render_save_section(edited_records, run_dir):
    """Render save manual review decisions section."""
    decisions = manual_review_decisions_from_rows(edited_records, run_dir.name)
    st.markdown("### 1. 💾 Save Manual Review Decisions")
    st.caption(
        "يحفظ هذه التعديلات في قاعدة البيانات كقواعد ثابتة "
        "حتى يتعلمها الذكاء الاصطناعي ويطبقها في الطلبيات "
        "القادمة."
    )
    if decisions:
        items_list = "، ".join(d.item_name for d in decisions)
        st.info(f"✨ سيتم حفظ **{len(decisions)}** أصناف: {items_list}")
    else:
        st.warning("⚠️ لا يوجد أي أصناف معدلة ليتم حفظها.")
    if st.button("Save Manual Review Decisions", disabled=not decisions):
        count = save_manual_review_rows(edited_records, run_dir.name)
        st.success(f"✅ Saved {count} decision(s)!")


def _render_remove_not_matching_section(edited_records, run_dir):
    """Render remove not matching items section."""
    not_matching_rows = _get_not_matching_rows(edited_records)
    st.markdown("### 2. 🗑️ Remove Not Matching From Cart")
    st.caption(
        "يقوم بحذف الأصناف التي حددتها كـ (غير مطابقة) "
        "من سلة المشتريات على موقع المورد."
    )
    _show_not_matching_info(not_matching_rows)
    if st.button("Remove Not Matching From Cart", disabled=not not_matching_rows):
        start_not_matching_removal(edited_records, run_dir, st)
        st.success("Not-matching cart-removal flow started.")
        st.rerun()


def _get_not_matching_rows(edited_records):
    """Extract not matching rows from edited records."""
    not_matching_values = {"1", "true", "yes", "y", "true"}
    return [
        r for r in edited_records
        if r.get("not_matching") is True
        or str(r.get("not_matching") or "").lower() in not_matching_values
    ]


def _show_not_matching_info(not_matching_rows):
    """Show info message for not matching rows."""
    if not_matching_rows:
        items_list = "، ".join(str(r.get("item_name")) for r in not_matching_rows)
        st.info(
            f"✨ سيتم إزالة **{len(not_matching_rows)}** أصناف من السلة: {items_list}"
        )
    else:
        st.warning("⚠️ لم تقم بتحديد أي صنف كـ (غير مطابق) لإزالته من السلة.")


def _render_search_corrected_section(edited_records, run_dir):
    """Render search corrected items section."""
    corrected_rows = [r for r in edited_records if _has_correction(r)]
    st.markdown("### 3. 🔍 Search Corrected Items")
    st.caption(
        "يقوم بالبحث عن الأصناف التي أدخلت لها (اسماً صحيحاً) "
        "أو (كوداً صحيحاً) ليعيد مطابقتها وإضافتها للسلة."
    )
    _show_corrected_info(corrected_rows)
    if st.button("Search Corrected Items", disabled=not corrected_rows):
        start_corrected_item_search(edited_records, run_dir, st)
        st.success("Corrected-item match-only search started.")
        st.rerun()


def _show_corrected_info(corrected_rows):
    """Show info message for corrected rows."""
    if corrected_rows:
        items_str = "، ".join(str(r.get("item_name")) for r in corrected_rows)
        st.info(
            f"✨ سيتم إعادة البحث عن **{len(corrected_rows)}** أصناف مصححة: {items_str}"
        )
    else:
        st.warning("⚠️ لم تقم بتصحيح اسم أو كود أي صنف لإعادة البحث عنه.")


__all__ = [
    "render_manual_review_editor",
    "manual_review_store_or_stop",
    "start_not_matching_removal",
    "start_corrected_item_search",
    "render_running_search_controls",
]
