"""Input and data conversion logic for manual review."""

from __future__ import annotations

from pathlib import Path

from ..core.manual_review_hints import hint_key
from ..core.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)


# ============ Data Conversion Functions ============


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


# ============ Row Helpers ============


def editable_manual_review_rows(
    rows: list[dict[str, str]], store: ManualReviewStore | None = None
) -> list[dict[str, object]]:
    """Return UI rows with saved manual decisions and their source displayed."""
    saved_decisions_map = _load_saved_decisions_batch(rows, store) if store else {}
    editable = []
    for row in rows:
        item = _editable_row(row)
        key = hint_key(_clean(item.get("item_code")), _clean(item.get("item_name")))
        saved = saved_decisions_map.get(key)
        _apply_saved_decision(item, saved)
        editable.append(item)
    return editable


def _load_saved_decisions_batch(
    rows: list[dict[str, str]], store: ManualReviewStore
) -> dict[tuple[str, str], ManualReviewDecision]:
    """Load all saved decisions for rows in one database query."""
    items = [{"code": _clean(r.get("item_code")), "name": _clean(r.get("item_name"))} for r in rows]
    return store.lookup_many(items)


def _editable_row(row: dict[str, str]) -> dict[str, object]:
    item = dict(row)
    item.setdefault("approved_match", False)
    item.setdefault("not_matching", False)
    item.setdefault("correct_store_product_id", "")
    item.setdefault("correct_product_name", "")
    item.setdefault("correct_query", item.get("matched_query", ""))
    item.setdefault("decision_source", "run_artifact")
    return item


def _apply_saved_decision(
    item: dict[str, object], saved: ManualReviewDecision | None
) -> None:
    if not saved:
        return
    item["approved_match"] = saved.approved
    item["not_matching"] = saved.manual_decision == "not_matching"
    item["correct_store_product_id"] = saved.correct_store_product_id
    item["correct_product_name"] = saved.correct_product_name
    item["correct_query"] = saved.correct_query
    item["decision_source"] = "saved_manual_review"


__all__ = [
    "save_manual_review_rows",
    "manual_review_decisions_from_rows",
    "editable_manual_review_rows",
]
