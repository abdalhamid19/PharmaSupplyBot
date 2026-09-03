"""Per-item offering-store snapshot capture for order-run persistence.

Tawreed returns every store that stocks a product, but the ordering flow keeps
only the store it selected and discards the rest. This module parks the full
list on the bot so the artifact writer can persist all of them, following the
same pattern the codebase already uses for ``last_selected_store_name``.

The snapshot MUST be cleared between items (see ``_reset_last_item_state``).
A leak there would attribute item N's warehouses to item N+1 — data that looks
plausible and is wrong, which is worse than missing data.
"""

from __future__ import annotations

from typing import Any, Iterable

SOURCE_STORE_DETAILS = "store_details"
SOURCE_SEARCH_ROW = "search"


def record_store_rows(bot, rows: Iterable[dict[str, Any]], source: str) -> None:
    """Store every offering-store row for the active item on the bot.

    Empty input is ignored so a failed follow-up API call cannot erase a good
    earlier capture for the same item.
    """
    captured = list(rows or [])
    if not captured:
        return
    bot.last_store_rows = captured
    bot.last_store_rows_source = source


def record_store_selections(
    bot, selections: Iterable[tuple[dict[str, Any], int]]
) -> None:
    """Store which stores were ordered from and how much of each."""
    bot.last_store_selections = [
        (store, int(quantity)) for store, quantity in selections
    ]


def record_store_choice(bot, store: dict[str, Any] | None) -> None:
    """Record the store the strategy chose without ordering anything.

    Used by match-only, where a winner exists but no quantity is committed. The
    zero quantity is what keeps ``ordered_qty`` honest: ``is_winner`` means "the
    strategy picked this store", ``ordered_qty`` means "this much was ordered".
    """
    if store:
        record_store_selections(bot, [(store, 0)])


def captured_store_rows(bot) -> list[dict[str, Any]]:
    """Return the offering-store rows captured for the active item."""
    return list(getattr(bot, "last_store_rows", None) or [])


def captured_store_selections(bot) -> list[tuple[dict[str, Any], int]]:
    """Return the (store, ordered quantity) pairs for the active item."""
    return list(getattr(bot, "last_store_selections", None) or [])


def captured_store_source(bot) -> str:
    """Return where the captured store rows came from."""
    return str(getattr(bot, "last_store_rows_source", "") or "")


def clear_store_snapshot(bot) -> None:
    """Reset the captured snapshot before the next item is processed."""
    bot.last_store_rows = []
    bot.last_store_selections = []
    bot.last_store_rows_source = ""


__all__ = [
    "SOURCE_STORE_DETAILS",
    "SOURCE_SEARCH_ROW",
    "record_store_rows",
    "record_store_selections",
    "record_store_choice",
    "captured_store_rows",
    "captured_store_selections",
    "captured_store_source",
    "clear_store_snapshot",
]
