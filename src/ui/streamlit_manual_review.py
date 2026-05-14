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


def render_manual_review_editor(rows: list[dict[str, str]], run_dir: Path) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    store = ManualReviewStore()
    editable_rows = editable_manual_review_rows(rows, store)
    edited = st.data_editor(pd.DataFrame(editable_rows), use_container_width=True)
    if st.button("Save Manual Review Decisions"):
        count = save_manual_review_rows(edited.to_dict("records"), run_dir.name)
        st.success(f"Saved {count} manual-review decision(s).")
    if st.button("Remove Not Matching From Cart"):
        start_not_matching_removal(edited.to_dict("records"), run_dir, st)
        st.success("Not-matching cart-removal flow started.")


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
