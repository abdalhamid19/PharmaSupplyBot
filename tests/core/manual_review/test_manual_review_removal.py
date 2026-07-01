"""Tests for building cart-removal inputs from manual-review decisions."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.core.manual_review.manual_review_removal import (
    cart_items_from_manual_review_csv,
    cart_items_from_saved_not_matching,
)
from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore


class ManualReviewRemovalTests(unittest.TestCase):
    """Validate manual-review rows can drive cart removal."""

    def test_csv_not_matching_rows_become_cart_items(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manual_review.csv"
            path.write_text(
                "item_code,item_name,manual_decision\n1,Panadol,not_matching\n",
                encoding="utf-8",
            )

            items = cart_items_from_manual_review_csv(path)

        self.assertEqual(items[0].code, "1")
        self.assertEqual(items[0].name, "Panadol")

    @patch("src.core.manual_review.manual_review_store.ManualReviewStore.list_decisions")
    def test_saved_not_matching_decisions_become_cart_items(self, mock_list) -> None:
        mock_list.return_value = [
            ManualReviewDecision(
                "1", "Panadol", False, manual_decision="not_matching"
            )
        ]
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            items = cart_items_from_saved_not_matching(store)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Panadol")


if __name__ == "__main__":
    unittest.main()
