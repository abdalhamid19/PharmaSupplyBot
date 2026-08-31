"""Tests for per-item offering-store snapshot capture on the bot."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.tawreed.store.tawreed_store_snapshot import (
    captured_store_rows,
    captured_store_selections,
    clear_store_snapshot,
    record_store_choice,
    record_store_rows,
    record_store_selections,
)


def _bot() -> SimpleNamespace:
    """Return a bot stub with no snapshot attributes set."""
    return SimpleNamespace()


class RecordStoreRowsTests(unittest.TestCase):
    """All offering stores for the active item are held on the bot."""

    def test_records_rows_and_source(self) -> None:
        """The source distinguishes complete data from a single-candidate fallback."""
        bot = _bot()
        record_store_rows(bot, [{"storeId": 1}, {"storeId": 2}], "store_details")
        self.assertEqual(len(captured_store_rows(bot)), 2)
        self.assertEqual(bot.last_store_rows_source, "store_details")

    def test_copies_the_incoming_list(self) -> None:
        """The caller keeps mutating its list while iterating stores."""
        bot, rows = _bot(), [{"storeId": 1}]
        record_store_rows(bot, rows, "store_details")
        rows.append({"storeId": 2})
        self.assertEqual(len(captured_store_rows(bot)), 1)

    def test_ignores_empty_rows_without_clearing_source(self) -> None:
        """An empty API response must not erase a good earlier capture."""
        bot = _bot()
        record_store_rows(bot, [{"storeId": 1}], "store_details")
        record_store_rows(bot, [], "store_details")
        self.assertEqual(len(captured_store_rows(bot)), 1)

    def test_reads_safely_from_a_bot_without_attributes(self) -> None:
        """Older bot objects and test doubles must not raise."""
        self.assertEqual(captured_store_rows(_bot()), [])
        self.assertEqual(captured_store_selections(_bot()), [])


class RecordStoreSelectionsTests(unittest.TestCase):
    """Which stores were actually ordered from, and how much of each."""

    def test_records_store_and_quantity_pairs(self) -> None:
        """Split quantities across stores must be preserved per store."""
        bot = _bot()
        record_store_selections(bot, [({"storeId": 1}, 5), ({"storeId": 2}, 3)])
        selections = captured_store_selections(bot)
        self.assertEqual([qty for _, qty in selections], [5, 3])

    def test_coerces_quantities_to_int(self) -> None:
        """Dialog input can produce float quantities."""
        bot = _bot()
        record_store_selections(bot, [({"storeId": 1}, 5.0)])
        self.assertEqual(captured_store_selections(bot)[0][1], 5)


class ClearStoreSnapshotTests(unittest.TestCase):
    """Leaking one item's stores into the next would corrupt data silently."""

    def test_clears_rows_selections_and_source(self) -> None:
        """Called from _reset_last_item_state before every item."""
        bot = _bot()
        record_store_rows(bot, [{"storeId": 1}], "store_details")
        record_store_selections(bot, [({"storeId": 1}, 5)])
        clear_store_snapshot(bot)
        self.assertEqual(captured_store_rows(bot), [])
        self.assertEqual(captured_store_selections(bot), [])
        self.assertEqual(bot.last_store_rows_source, "")

    def test_clear_is_safe_on_a_fresh_bot(self) -> None:
        """Clearing before any capture must not raise."""
        clear_store_snapshot(_bot())


class BotResetIntegrationTests(unittest.TestCase):
    """The real bot must clear the snapshot between items."""

    def test_reset_last_item_state_clears_the_snapshot(self) -> None:
        """This is the guard against cross-item store contamination."""
        from src.tawreed.tawreed_bot_core import TawreedBotCore

        bot = TawreedBotCore.__new__(TawreedBotCore)
        record_store_rows(bot, [{"storeId": 1}], "store_details")
        record_store_selections(bot, [({"storeId": 1}, 5)])
        bot._reset_last_item_state()
        self.assertEqual(captured_store_rows(bot), [])
        self.assertEqual(captured_store_selections(bot), [])


if __name__ == "__main__":
    unittest.main()
