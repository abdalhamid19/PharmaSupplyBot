"""Helper functions for cart removal flow."""

from __future__ import annotations

from typing import Iterable

from ..core.cart_removal_items import CartRemovalItem
from ..core.utils.excel import Item
from .tawreed_cart_removal_selectors import CartRemovalTarget
from .tawreed_search_logic import require_product_match


def resolve_cart_removal_targets(bot, page, items: Iterable[CartRemovalItem]):
    """Resolve Tawreed product names for removal items."""
    targets = []
    for item in items:
        if _cart_stop_requested(bot, item):
            break
        names = [item.name]
        try:
            it = Item(code=item.code, name=item.name, qty=1)
            match, _ = require_product_match(bot, page, it, require_available=False)
            names.extend(
                [
                    str(match.data.get(k) or "")
                    for k in ("productName", "productNameAr", "productNameEn")
                ]
            )
        except Exception as e:
            _log(bot, f"Could not resolve name for {item.name}: {e}")
        targets.append(CartRemovalTarget(item, _unique(names)))
    return targets


def _cart_stop_requested(bot, item: CartRemovalItem) -> bool:
    """Return whether cart-removal processing should stop before one item."""
    if not getattr(bot, "_stop_requested", lambda: False)():
        return False
    bot.log(f"Stop requested before cart item {item.code} / {item.name}.")
    return True


def _unique(names: list[str]) -> list[str]:
    """Return unique non-empty names while preserving original order."""
    res, seen = [], set()
    for n in names:
        t = str(n or "").strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            res.append(t)
    return res


def _log(bot, message: str) -> None:
    """Log through the bot when available, else print ASCII-safe text."""
    logger = getattr(bot, "log", None)
    if logger:
        logger(message)
        return
    print(message.encode("ascii", errors="replace").decode("ascii"))


__all__ = [
    "resolve_cart_removal_targets",
    "_cart_stop_requested",
    "_unique",
    "_log",
]
