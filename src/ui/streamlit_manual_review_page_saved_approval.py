"""Approval conversion functions for saved decisions page."""

from __future__ import annotations

import dataclasses
import streamlit as st

from .streamlit_manual_review_db import manual_review_store_or_stop


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
    "_handle_approval_conversion",
    "_render_conversion_button",
    "_convert_to_approved",
]
