"""Manual-review learning controls for Streamlit result runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from .streamlit_manual_review_remove import start_not_matching_removal
from .streamlit_manual_review_rows import editable_manual_review_rows
from .streamlit_manual_review_search import start_corrected_item_search


def render_manual_review_editor(rows: list[dict[str, str]], run_dir: Path) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    store = ManualReviewStore()
    editable_rows = editable_manual_review_rows(rows, store)
    
    selected_columns = None
    if editable_rows:
        all_cols = list(editable_rows[0].keys())
        default_cols = [
            "item_code", "item_name", "matched_product_name_en", "item_qty", "status",
            "approved_match", "not_matching", 
            "correct_store_product_id", "correct_product_name", "correct_query"
        ]
        # Ensure default cols exist
        default_cols = [c for c in default_cols if c in all_cols]
        # Add any remaining columns that weren't specified in the default list
        for c in all_cols:
            if c not in default_cols:
                default_cols.append(c)
                
        selected_columns = st.multiselect(
            "اختر الأعمدة المراد عرضها (Select Columns to Display):",
            options=all_cols,
            default=default_cols,
            key="manual_review_columns_multiselect"
        )
        
    edited = st.data_editor(
        pd.DataFrame(editable_rows), 
        use_container_width=True,
        column_order=selected_columns if selected_columns else None
    )
    edited_records = edited.to_dict("records")
    
    # 1. Save Decisions
    decisions = manual_review_decisions_from_rows(edited_records, run_dir.name)
    st.markdown("### 1. 💾 Save Manual Review Decisions")
    st.caption("يحفظ هذه التعديلات في قاعدة البيانات كقواعد ثابتة حتى يتعلمها الذكاء الاصطناعي ويطبقها في الطلبيات القادمة.")
    if decisions:
        st.info(f"✨ سيتم حفظ **{len(decisions)}** أصناف: " + "، ".join(d.item_name for d in decisions))
    else:
        st.warning("⚠️ لا يوجد أي أصناف معدلة ليتم حفظها.")
    if st.button("Save Manual Review Decisions", disabled=not decisions):
        count = save_manual_review_rows(edited_records, run_dir.name)
        st.success(f"Saved {count} manual-review decision(s).")
        st.rerun()

    # 2. Remove Not Matching
    not_matching_rows = [r for r in edited_records if str(r.get("not_matching") or "").lower() in {"1", "true", "yes", "y", "true"}]
    # Also handle boolean True since it's a dataframe
    not_matching_rows = [r for r in edited_records if r.get("not_matching") is True or str(r.get("not_matching") or "").lower() in {"1", "true", "yes", "y"}]
    
    st.markdown("### 2. 🗑️ Remove Not Matching From Cart")
    st.caption("يقوم بحذف الأصناف التي حددتها كـ (غير مطابقة) من سلة المشتريات على موقع المورد.")
    if not_matching_rows:
        st.info(f"✨ سيتم إزالة **{len(not_matching_rows)}** أصناف من السلة: " + "، ".join(str(r.get("item_name")) for r in not_matching_rows))
    else:
        st.warning("⚠️ لم تقم بتحديد أي صنف كـ (غير مطابق) لإزالته من السلة.")
    if st.button("Remove Not Matching From Cart", disabled=not not_matching_rows):
        start_not_matching_removal(edited_records, run_dir, st)
        st.success("Not-matching cart-removal flow started.")
        st.rerun()

    # 3. Search Corrected
    from ..core.manual_review_corrections import _has_correction
    corrected_rows = [r for r in edited_records if _has_correction(r)]
    st.markdown("### 3. 🔍 Search Corrected Items")
    st.caption("يقوم بالبحث عن الأصناف التي أدخلت لها (اسماً صحيحاً) أو (كوداً صحيحاً) ليعيد مطابقتها وإضافتها للسلة.")
    if corrected_rows:
        st.info(f"✨ سيتم إعادة البحث عن **{len(corrected_rows)}** أصناف مصححة: " + "، ".join(str(r.get("item_name")) for r in corrected_rows))
    else:
        st.warning("⚠️ لم تقم بتصحيح اسم أو كود أي صنف لإعادة البحث عنه.")
    if st.button("Search Corrected Items", disabled=not corrected_rows):
        start_corrected_item_search(edited_records, run_dir, st)
        st.success("Corrected-item match-only search started.")
        st.rerun()


def save_manual_review_rows(
    rows: list[dict], run_id: str, store_path: Path = DEFAULT_MANUAL_REVIEW_DB
) -> int:
    """Persist edited manual-review rows and return the saved count."""
    store = ManualReviewStore(store_path)
    decisions = manual_review_decisions_from_rows(rows, run_id)
    for decision in decisions:
        store.upsert(decision)
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
