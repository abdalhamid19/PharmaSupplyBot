"""Row helpers for Streamlit manual-review editing."""

from __future__ import annotations

from ..core.manual_review_store import ManualReviewDecision, ManualReviewStore


def editable_manual_review_rows(
    rows: list[dict[str, str]], store: ManualReviewStore | None = None
) -> list[dict[str, object]]:
    """Return UI rows with saved manual decisions and their source displayed."""
    editable = []
    for row in rows:
        item = _editable_row(row)
        _apply_saved_decision(item, _saved_decision(store, item))
        editable.append(item)
    return editable


def _editable_row(row: dict[str, str]) -> dict[str, object]:
    item = dict(row)
    item.setdefault("approved_match", False)
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
    item["correct_store_product_id"] = saved.correct_store_product_id
    item["correct_product_name"] = saved.correct_product_name
    item["correct_query"] = saved.correct_query
    item["decision_source"] = "saved_manual_review"


def _saved_decision(
    store: ManualReviewStore | None, item: dict[str, object]
) -> ManualReviewDecision | None:
    if not store:
        return None
    return store.lookup(_clean(item.get("item_code")), _clean(item.get("item_name")))


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
