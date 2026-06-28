"""Data conversion functions for manual review in Streamlit."""

from pathlib import Path

from ..core.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)


def save_manual_review_rows(
    rows: list[dict], run_id: str, store_path: Path = DEFAULT_MANUAL_REVIEW_DB
) -> int:
    """Persist edited manual-review rows and return the saved count."""
    store = ManualReviewStore(store_path)
    decisions = manual_review_decisions_from_rows(rows, run_id)
    store.upsert_batch(decisions)
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


def _decisions_from_rows_internal(rows: list[dict], run_id: str) -> list[ManualReviewDecision]:
    """Return saved decisions represented by edited Streamlit rows."""
    decisions = []
    for row in rows:
        decision = _decision_from_row(row, run_id)
        if decision:
            decisions.append(decision)
    return decisions


def _save_rows(rows: list[dict], run_id: str, store_path: Path = DEFAULT_MANUAL_REVIEW_DB) -> int:
    """Persist edited manual-review rows and return the saved count."""
    store = ManualReviewStore(store_path)
    decisions = _decisions_from_rows_internal(rows, run_id)
    store.upsert_batch(decisions)
    return len(decisions)


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
