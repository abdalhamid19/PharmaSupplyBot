"""Tests for the ``--sort-by-net`` CLI flag and its comparator behaviour."""

from __future__ import annotations

import unittest
from argparse import Namespace
from unittest.mock import MagicMock

from src.cli.commands.cli_order import _cheaper, apply_order_overrides


class SortByNetComparatorTests(unittest.TestCase):
    """The flag flips the tie-break from raw purchase to net price."""

    def test_default_uses_purchase_price(self) -> None:
        """Without the flag, lower raw purchase wins."""
        candidate = {"purchase_price": 80.0, "public_price": 100.0, "discount_percent": 0.0}
        current = {"purchase_price": 100.0, "public_price": 100.0, "discount_percent": 0.0}
        self.assertTrue(_cheaper(candidate, current))

    def test_sort_by_net_picks_lowest_net(self) -> None:
        """With the flag, the lower post-discount net wins."""
        # Candidate: 90 × (1 − 50%) = 45; Current: 100 × (1 − 0%) = 100.
        # Lower net → candidate should beat current.
        candidate = {"purchase_price": 90.0, "public_price": 90.0, "discount_percent": 50.0}
        current = {"purchase_price": 100.0, "public_price": 100.0, "discount_percent": 0.0}
        self.assertTrue(_cheaper(candidate, current, sort_by_net=True))

    def test_sort_by_net_falls_back_to_purchase_when_net_missing(self) -> None:
        """When net cannot be computed, the original rule decides."""
        candidate = {"purchase_price": 70.0, "public_price": None, "discount_percent": 0.0}
        current = {"purchase_price": 80.0, "public_price": None, "discount_percent": 0.0}
        self.assertTrue(_cheaper(candidate, current, sort_by_net=True))

    def test_sort_by_net_equal_falls_through_to_discount_tiebreak(self) -> None:
        """Identical nets resolve by the higher discount percent."""
        candidate = {"purchase_price": 100.0, "public_price": 100.0, "discount_percent": 30.0}
        current = {"purchase_price": 100.0, "public_price": 100.0, "discount_percent": 10.0}
        self.assertTrue(_cheaper(candidate, current, sort_by_net=True))


class ApplyOrderOverridesTests(unittest.TestCase):
    """The CLI flag is written into ``warehouse_strategy``."""

    def test_sort_by_net_is_written_when_present(self) -> None:
        config = MagicMock()
        config.warehouse_strategy = {"mode": "first_available"}
        apply_order_overrides(config, Namespace(sort_by_net=True))
        self.assertEqual(config.warehouse_strategy["sort_by_net"], True)

    def test_sort_by_net_default_is_preserved(self) -> None:
        config = MagicMock()
        config.warehouse_strategy = {"mode": "first_available"}
        apply_order_overrides(config, Namespace())
        self.assertNotIn("sort_by_net", config.warehouse_strategy)


if __name__ == "__main__":
    unittest.main()