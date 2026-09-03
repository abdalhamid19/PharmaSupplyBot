"""Shared match-only snapshot recording for the store selected by strategy."""

from __future__ import annotations

from .tawreed_store_snapshot import (
    SOURCE_SEARCH_ROW,
    record_store_choice,
    record_store_rows,
)


def record_single_store_match_only_choice(bot, store: dict) -> None:
    """Record a single search-row store as the match-only winner.

    A single-store product never opens the stores dialog. Its search row is
    therefore both the complete offering-store snapshot and the chosen store.
    """
    record_store_rows(bot, [store], SOURCE_SEARCH_ROW)
    record_store_choice(bot, store)


def record_match_only_choice(bot, choice) -> None:
    """Record a strategy choice when the multi-store chooser returned one."""
    if choice:
        record_store_choice(bot, choice.store)


__all__ = ["record_single_store_match_only_choice", "record_match_only_choice"]
