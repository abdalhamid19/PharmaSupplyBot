"""Tests for a match-only store choice without an order quantity."""

from __future__ import annotations

from types import SimpleNamespace

from src.tawreed.store.tawreed_store_snapshot import (
    captured_store_selections,
    record_store_choice,
)


def test_record_store_choice_ignores_no_store() -> None:
    """A failed strategy selection leaves the active snapshot unchanged."""
    bot = SimpleNamespace()
    record_store_choice(bot, None)
    assert captured_store_selections(bot) == []


def test_record_store_choice_marks_a_zero_quantity_winner() -> None:
    """Match-only identifies a winner without claiming an order was made."""
    bot = SimpleNamespace()
    store = {"storeId": 4, "storeProductId": 77}
    record_store_choice(bot, store)
    assert captured_store_selections(bot) == [(store, 0)]
