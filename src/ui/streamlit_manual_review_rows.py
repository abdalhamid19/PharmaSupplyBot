"""Row helpers for Streamlit manual-review editing."""

from __future__ import annotations

from ..core.manual_review_store import ManualReviewDecision, ManualReviewStore
from ..core.manual_review_hints import hint_key


def editable_manual_review_rows(
    rows: list[dict[str, str]], store: ManualReviewStore | None = None
) -> list[dict[str, object]]:
    """Return UI rows with saved manual decisions and their source displayed."""
    # ⚡ Batch load all saved decisions in one query
    saved_decisions_map = _load_saved_decisions_batch(rows, store) if store else {}
    
    editable = []
    for row in rows:
        item = _editable_row(row)
        # Lookup from pre-loaded map (O(1) instead of database query)
        key = hint_key(_clean(item.get("item_code")), _clean(item.get("item_name")))
        saved = saved_decisions_map.get(key)
        _apply_saved_decision(item, saved)
        editable.append(item)
    return editable


def _load_saved_decisions_batch(
    rows: list[dict[str, str]], store: ManualReviewStore
) -> dict[tuple[str, str], ManualReviewDecision]:
    """Load all saved decisions for rows in one database query."""
    # Create lightweight item objects for lookup_many
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


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
