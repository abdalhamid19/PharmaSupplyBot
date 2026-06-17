"""Tests for Tawreed search logic and match decision making."""

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from src.core.manual_review_store import (
    DEFAULT_MANUAL_REVIEW_DB,
    ManualReviewDecision,
    ManualReviewStore,
)
from src.core.utils.excel import Item
from src.tawreed.tawreed_search_logic import _match_decision


class TawreedSearchLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "manual_review.sqlite3"
        
        # Patch the DEFAULT_MANUAL_REVIEW_DB path inside manual_review_runtime
        import src.core.manual_review_runtime
        self.original_db_path = src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB
        src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB = self.db_path

        self.store = ManualReviewStore(self.db_path)
        self.item = Item(code="TEST1", name="Product X", qty="1")
        self.bot_mock = MagicMock()
        self.bot_mock.config.matching.candidate_top_k = 5

    def tearDown(self) -> None:
        import src.core.manual_review_runtime
        src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB = self.original_db_path
        self.temp_dir.cleanup()

    def test_match_decision_returns_forced_manual_review_match(self) -> None:
        # Save a manual review decision forcing a specific storeProductId
        decision = ManualReviewDecision(
            item_code="TEST1", item_name="Product X", approved=True,
            correct_store_product_id="s123", manual_decision="approved_match"
        )
        self.store.upsert(decision)

        results = [
            ("query1", [{"storeProductId": "s999", "productNameEn": "Other Product"}]),
            ("query2", [
                {"storeProductId": "s123", "productNameEn": "The Right Product"},
                {"storeProductId": "s456", "productNameEn": "Product X but wrong"}
            ])
        ]

        # Call _match_decision
        match_decision = _match_decision(self.bot_mock, self.item, results)
        
        self.assertIsNotNone(match_decision)
        self.assertIsNotNone(match_decision.best_match)
        self.assertEqual(match_decision.best_match.score, 999.0)
        self.assertEqual(match_decision.best_match.data["storeProductId"], "s123")
        self.assertEqual(match_decision.final_reason, "Approved by saved manual review (ID match).")


if __name__ == "__main__":
    unittest.main()
