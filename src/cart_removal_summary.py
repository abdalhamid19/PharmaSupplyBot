"""Artifacts for Tawreed cart-removal runs."""

from __future__ import annotations

from dataclasses import dataclass

from .cart_removal_items import CartRemovalItem
from .tawreed_artifacts import append_csv_artifact


@dataclass(frozen=True)
class CartRemovalSummary:
    """One cart-removal result row."""

    removed_count: int
    status: str
    reason: str


def append_cart_removal_summary(
    profile_key: str,
    item: CartRemovalItem,
    summary: CartRemovalSummary,
) -> None:
    """Append one cart-removal summary row."""
    append_csv_artifact(
        profile_key,
        "cart_removal_summary",
        [
            {
                "item_code": item.code,
                "item_name": item.name,
                "removed_count": summary.removed_count,
                "status": summary.status,
                "reason": summary.reason,
            }
        ],
    )
