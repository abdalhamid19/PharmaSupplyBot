"""Artifacts for Tawreed cart-removal runs."""

from __future__ import annotations

from dataclasses import dataclass

from .cart_removal_items import CartRemovalItem


@dataclass(frozen=True)
class CartRemovalSummary:
    """One cart-removal result row."""

    removed_count: int
    status: str
    reason: str
