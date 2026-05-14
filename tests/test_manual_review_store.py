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
            store.upsert(
                ManualReviewDecision(
                    "1", "A", False, "", "A New", manual_decision="needs_correction"
                )
            )

            decisions = store.list_decisions()

        self.assertEqual(len(decisions), 1)
        self.assertFalse(decisions[0].approved)
        self.assertEqual(decisions[0].correct_product_name, "A New")

    def test_stores_not_matching_decision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            store.upsert(
                ManualReviewDecision(
                    "1", "A", False, "store-1", manual_decision="not_matching"
                )
            )

            decision = store.lookup("1", "A")

        self.assertEqual(decision.manual_decision, "not_matching")

    def test_decision_persists_across_store_instances(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision(
                    " 001.0 ",
                    "  Panadol   Extra ",
                    True,
                    correct_store_product_id="store-2",
                    correct_query="Panadol Extra 24",
                )
            )

            decision = ManualReviewStore(db_path).lookup("001", "panadol extra")

        self.assertIsNotNone(decision)
        self.assertTrue(decision.approved)
        self.assertEqual(decision.correct_store_product_id, "store-2")
        self.assertEqual(decision.correct_query, "Panadol Extra 24")


if __name__ == "__main__":
    unittest.main()
