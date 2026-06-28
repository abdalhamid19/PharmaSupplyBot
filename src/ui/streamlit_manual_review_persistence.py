"""Persistence logic for manual review decisions in Streamlit."""

from pathlib import Path

import streamlit as st

from .streamlit_manual_review_remove import start_not_matching_removal
from .streamlit_manual_review_search import start_corrected_item_search
from .streamlit_manual_review_data import (
    _decisions_from_rows_internal,
    _save_rows,
)


def _render_action_sections(edited_records, run_dir):
    """Render all action sections (save, remove, search)."""
    _render_save_section(edited_records, run_dir)
    _render_remove_not_matching_section(edited_records, run_dir)
    _render_search_corrected_section(edited_records, run_dir)


def _render_save_section(edited_records, run_dir):
    """Render save manual review decisions section."""
    decisions = _decisions_from_rows_internal(edited_records, run_dir.name)
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
        count = _save_rows(edited_records, run_dir.name)
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
