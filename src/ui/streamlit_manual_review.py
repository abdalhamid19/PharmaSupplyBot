"""Manual-review learning controls for Streamlit result runs."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from .streamlit_manual_review_db import manual_review_store_or_stop
from .streamlit_manual_review_remove import start_not_matching_removal
from .streamlit_manual_review_rows import editable_manual_review_rows
from .streamlit_manual_review_search import start_corrected_item_search


def render_manual_review_editor(rows: list[dict[str, str]], run_dir: Path) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    
    store = manual_review_store_or_stop()
    editable_rows = _load_editable_rows(rows, store, run_dir)
    edited_records = _render_editor_ui(editable_rows)
    _update_cache_after_edit(editable_rows, edited_records, run_dir)
    _render_action_sections(edited_records, run_dir)


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


def _render_action_sections(edited_records: list[dict], run_dir: Path) -> None:
    """Render all action sections (save, remove, search)."""
    _render_save_section(edited_records, run_dir)
    _render_remove_not_matching_section(edited_records, run_dir)
    _render_search_corrected_section(edited_records, run_dir)


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


def _render_save_section(edited_records, run_dir):
    """Render save manual review decisions section."""
    decisions = manual_review_decisions_from_rows(edited_records, run_dir.name)
    st.markdown("### 1. 💾 Save Manual Review Decisions")
    st.caption(
        "يحفظ هذه التعديلات في قاعدة البيانات كقواعد ثابتة حتى يتعلمها "
        "الذكاء الاصطناعي ويطبقها في الطلبيات القادمة."
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
    st.caption("يقوم بحذف الأصناف التي حددتها كـ (غير مطابقة) من سلة المشتريات على موقع المورد.")
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
            f"✨ سيتم إزالة **{len(not_matching_rows)}** أصناف من السلة: "
            f"{items_list}"
        )
    else:
        st.warning("⚠️ لم تقم بتحديد أي صنف كـ (غير مطابق) لإزالته من السلة.")


def _render_search_corrected_section(edited_records, run_dir):
    """Render search corrected items section."""
    from ..core.manual_review_corrections import _has_correction
    corrected_rows = [r for r in edited_records if _has_correction(r)]
    st.markdown("### 3. 🔍 Search Corrected Items")
    st.caption(
        "يقوم بالبحث عن الأصناف التي أدخلت لها (اسماً صحيحاً) أو "
        "(كوداً صحيحاً) ليعيد مطابقتها وإضافتها للسلة."
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
            f"✨ سيتم إعادة البحث عن **{len(corrected_rows)}** "
            f"أصناف مصححة: {items_str}"
        )
    else:
        st.warning("⚠️ لم تقم بتصحيح اسم أو كود أي صنف لإعادة البحث عنه.")


def save_manual_review_rows(
    rows: list[dict], run_id: str, store_path: Path = DEFAULT_MANUAL_REVIEW_DB
) -> int:
    """Persist edited manual-review rows and return the saved count."""
    store = ManualReviewStore(store_path)
    decisions = manual_review_decisions_from_rows(rows, run_id)
    store.upsert_batch(decisions)  # ⚡ Batch upsert instead of loop
    return len(decisions)


def manual_review_decisions_from_rows(
    rows: list[dict], run_id: str
) -> list[ManualReviewDecision]:
    """Return saved decisions represented by edited Streamlit rows."""
    decisions = []
    for row in rows:
        decision = _decision_from_row(row, run_id)
        if decision:
            decisions.append(decision)
    return decisions


def _decision_from_row(row: dict, run_id: str) -> ManualReviewDecision | None:
    approved = bool(row.get("approved_match"))
    not_matching = bool(row.get("not_matching"))
    correction = _correction_fields(row)
    if not approved and not not_matching and not any(correction):
        return None
    manual_decision = _manual_decision(approved, not_matching)
    return ManualReviewDecision(
        item_code=_clean(row.get("item_code")),
        item_name=_clean(row.get("item_name")),
        approved=approved,
        correct_store_product_id=correction[0],
        correct_product_name=correction[1],
        correct_query=correction[2],
        run_id=run_id,
        manual_decision=manual_decision,
    )


def _correction_fields(row: dict) -> tuple[str, str, str]:
    return (
        _clean(row.get("correct_store_product_id")),
        _clean(row.get("correct_product_name")),
        _clean(row.get("correct_query")),
    )


def _manual_decision(approved: bool, not_matching: bool) -> str:
    if not_matching:
        return "not_matching"
    return "approved_match" if approved else "needs_correction"


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
