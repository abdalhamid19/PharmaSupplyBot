"""Tests for applying saved manual-review decisions during matching."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.core.manual_review_runtime import manual_review_match, manual_review_queries
from src.core.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.utils.excel import Item


class ManualReviewRuntimeTests(unittest.TestCase):
    """Validate runtime consumption of saved manual-review decisions."""

    def test_manual_review_queries_prepend_saved_correct_query(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision("1", "Panadol", False, correct_query="Pana 24")
            )
            with patch("src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB", db_path):
                queries = manual_review_queries(Item("1", "Panadol", 1), ["Panadol"])

        self.assertEqual(queries, ["Pana 24", "Panadol"])

    def test_manual_review_match_returns_saved_store_product_id(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision("1", "Panadol", True, "store-1")
            )
            with patch("src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB", db_path):
                decision = manual_review_match(
                    Item("1", "Panadol", 1),
                    [("Panadol", [{"storeProductId": "store-1", "productNameEn": "P"}])],
                )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.best_match.data["storeProductId"], "store-1")


if __name__ == "__main__":
    unittest.main()
