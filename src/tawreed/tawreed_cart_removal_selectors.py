"""Selectors and dataclasses for cart removal flow."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.cart_removal_items import CartRemovalItem


@dataclass(frozen=True)
class CartRemovalSelectors:
    """Selectors required to remove matching rows from the Tawreed cart."""

    cart_rows: str
    cart_delete_button: str
    cart_confirm_delete_button: str


@dataclass(frozen=True)
class CartRemovalTarget:
    """One cart-removal item plus every Tawreed name accepted for matching."""

    item: CartRemovalItem
    names: list[str]


__all__ = ["CartRemovalSelectors", "CartRemovalTarget"]
