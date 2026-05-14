"""Accepted match helpers shared by Tawreed search flow."""

from __future__ import annotations

from typing import Any

from ..core.utils.excel import Item


def accepted_no_match_result(bot, item: Item, decision, require_available: bool):
    """Return an AI-selected match from the no-match path after stock checks."""
    match = decision.best_match
    if require_available and available_quantity(match.data) <= 0:
        raise bot.skip_item_exception(
            f"Matched product is out of stock for '{item.name}'."
        )
    return match, match.query


def available_quantity(candidate: dict[str, Any]) -> int:
    """Return available quantity from a Tawreed candidate."""
    try:
        return int(candidate.get("availableQuantity") or 0)
    except (TypeError, ValueError):
        return 0
