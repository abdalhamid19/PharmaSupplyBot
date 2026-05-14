"""Tests for SQLite manual-review learning store."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.manual_review_store import ManualReviewDecision, ManualReviewStore


class ManualReviewStoreTests(unittest.TestCase):
    """Validate saving and reading manual-review decisions."""

    def test_upsert_and_lookup_decision_by_normalized_item_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            store.upsert(
                ManualReviewDecision(
                    item_code=" 123 ",
                    item_name="Panadol Extra",
                    approved=True,
                    correct_store_product_id="store-1",
                    correct_product_name="Panadol Extra 24 Tabs",
                    correct_query="Panadol Extra",
                    run_id="20260514_1252",
                )
            )

            decision = store.lookup("123", "panadol extra")

        self.assertIsNotNone(decision)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.correct_store_product_id, "store-1")

    def test_upsert_replaces_existing_decision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            store.upsert(ManualReviewDecision("1", "A", True, "old"))
            store.upsert(ManualReviewDecision("1", "A", False, "", "A New"))

            decisions = store.list_decisions()

        self.assertEqual(len(decisions), 1)
        self.assertFalse(decisions[0].approved)
        self.assertEqual(decisions[0].correct_product_name, "A New")


if __name__ == "__main__":
    unittest.main()
