"""Build cart-removal items from manual-review decisions."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ..cart.cart_removal_items import CartRemovalItem
from .manual_review_store import ManualReviewDecision, ManualReviewStore


def cart_items_from_manual_review_csv(path: Path) -> list[CartRemovalItem]:
    """Return cart-removal items marked as not matching in one manual-review CSV."""
    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    return _unique_items(_item_from_row(row) for row in rows if _is_not_matching(row))


def cart_items_from_saved_not_matching(store: ManualReviewStore | None = None):
    """Return cart-removal items from saved not-matching manual decisions."""
    active_store = store or ManualReviewStore()
    decisions = [
        decision for decision in active_store.list_decisions()
        if decision.manual_decision == "not_matching"
    ]
    return _unique_items(_item_from_decision(decision) for decision in decisions)


def _is_not_matching(row: dict[str, str]) -> bool:
    decision = _clean(row.get("manual_decision")).lower()
    flag = _clean(row.get("not_matching")).lower()
    return decision == "not_matching" or flag in {"1", "true", "yes", "y"}


def _item_from_row(row: dict[str, str]) -> CartRemovalItem:
    return CartRemovalItem(_clean(row.get("item_code")), _clean(row.get("item_name")))


def _item_from_decision(decision: ManualReviewDecision) -> CartRemovalItem:
    return CartRemovalItem(code=decision.item_code, name=decision.item_name)


def _unique_items(items: Iterable[CartRemovalItem]) -> list[CartRemovalItem]:
    seen: set[tuple[str, str]] = set()
    unique = []
    for item in items:
        key = (item.code.strip().lower(), item.name.strip().lower())
        if item.name and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _clean(value: object) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"nan", "none", "null"} else text
