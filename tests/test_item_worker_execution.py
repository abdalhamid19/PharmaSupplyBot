"""Tests for item-worker execution mode dispatch."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from src.cli.item_worker_execution import execute_order_worker


class ItemWorkerExecutionTests(unittest.TestCase):
    """Validate item worker dispatch for order and match-only modes."""

    def test_execute_order_worker_uses_match_only_bot_method(self) -> None:
        """Match-only workers call match_items_only instead of place_order_from_items."""
        bot = SimpleNamespace(
            match_only=True,
            match_items_only=Mock(),
            place_order_from_items=Mock(),
        )
        items = [object()]

        result = execute_order_worker(bot, items, "wardany")

        self.assertEqual(result["status"], "ok")
        bot.match_items_only.assert_called_once()
        bot.place_order_from_items.assert_not_called()

    def test_execute_order_worker_uses_order_bot_method_by_default(self) -> None:
        """Standard workers still call the real order flow."""
        bot = SimpleNamespace(
            match_items_only=Mock(),
            place_order_from_items=Mock(),
        )

        result = execute_order_worker(bot, [object()], "wardany")

        self.assertEqual(result["status"], "ok")
        bot.place_order_from_items.assert_called_once()
        bot.match_items_only.assert_not_called()


if __name__ == "__main__":
    unittest.main()
