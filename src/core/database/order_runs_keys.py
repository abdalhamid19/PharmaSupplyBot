"""Stable identity keys and dimension rows for the order-runs database.

Isolated from row conversion so the key rules — the one thing that must never
drift, or historical rows stop joining to new ones — live in a single place.
"""

from __future__ import annotations

from typing import Any

from ..manual_review.manual_review_hints import hint_key
from .order_runs_values import as_text


def order_run_item_key(item_code: Any, item_name: Any) -> str:
    """Return the item dimension key.

    Built from :func:`hint_key` so rows here can be joined against
    ``manual_review_decisions`` without a second normalisation rule.
    """
    code_key, name_key = hint_key(str(item_code or ""), str(item_name or ""))
    return f"{code_key}::{name_key}"


def run_key_for(profile_key: str, run_id: str) -> str:
    """Return the globally unique run key.

    ``run_id`` has minute precision and is only unique per command/profile, so
    two profiles started in the same minute would otherwise collide.
    """
    return f"{as_text(profile_key)}/{as_text(run_id)}"


def item_dimension_row(item_code: Any, item_name: Any, now: str) -> dict[str, Any]:
    """Return one ``items`` dimension row with both timestamps set.

    ``first_seen_at`` is never updated by later writes, so it must be correct
    on the very first insert.
    """
    return {
        "item_key": order_run_item_key(item_code, item_name),
        "item_code": as_text(item_code),
        "item_name": as_text(item_name),
        "first_seen_at": now,
        "last_seen_at": now,
    }


__all__ = [
    "order_run_item_key",
    "run_key_for",
    "item_dimension_row",
]
