"""Manual-review learning controls for Streamlit result runs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ..core.manual_review_store import ManualReviewDecision, ManualReviewStore


def render_manual_review_editor(rows: list[dict[str, str]], run_dir: Path) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    st.subheader("Manual Review")
    editable_rows = _editable_rows(rows)
    edited = st.data_editor(pd.DataFrame(editable_rows), use_container_width=True)
    if st.button("Save Manual Review Decisions"):
        count = save_manual_review_rows(edited.to_dict("records"), run_dir.name)
        st.success(f"Saved {count} manual-review decision(s).")


def save_manual_review_rows(rows: list[dict], run_id: str) -> int:
    """Persist edited manual-review rows and return the saved count."""
    store = ManualReviewStore()
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
    correct_id = _clean(row.get("correct_store_product_id"))
    correct_name = _clean(row.get("correct_product_name"))
    correct_query = _clean(row.get("correct_query"))
    if not approved and not any((correct_id, correct_name, correct_query)):
        return None
    return ManualReviewDecision(
        item_code=_clean(row.get("item_code")),
        item_name=_clean(row.get("item_name")),
        approved=approved,
        correct_store_product_id=correct_id,
        correct_product_name=correct_name,
        correct_query=correct_query,
        run_id=run_id,
    )


def _editable_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    editable = []
    for row in rows:
        item = dict(row)
        item.setdefault("approved_match", False)
        item.setdefault("correct_store_product_id", "")
        item.setdefault("correct_product_name", "")
        item.setdefault("correct_query", item.get("matched_query", ""))
        editable.append(item)
    return editable


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
