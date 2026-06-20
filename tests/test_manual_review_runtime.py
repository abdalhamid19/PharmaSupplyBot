"""Tests for applying saved manual-review decisions during matching."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.core.manual_review_runtime import (
    filter_manual_review_candidates,
    manual_review_match,
    manual_review_queries,
)
from src.core.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class ManualReviewRuntimeTests(unittest.TestCase):
    """Validate runtime consumption of saved manual-review decisions."""

    def test_lookup_many_loads_multiple_items_with_one_query(self) -> None:
        db = _FakeManualReviewDb()
        store = ManualReviewStore(database_manager=db)

        decisions = store.lookup_many(
            [Item("1", "Panadol", 1), Item("2", "Cataflam", 1)]
        )

        self.assertEqual(len(db.lookup_queries), 1)
        self.assertEqual(decisions[("1", "PANADOL")].correct_store_product_id, "s1")
        self.assertEqual(decisions[("2", "CATAFLAM")].correct_store_product_id, "s2")

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

    def test_saved_manual_decision_turns_previous_no_match_into_match(self) -> None:
        item = Item("CYTO", "CYTOTEC 200 MG 14 TABS +++IMP", 1)
        wrong_candidate = {"productNameEn": "SEBACLAR TONIC LOTION 200 ML"}
        self.assertIsNone(
            explain_best_product_match(item, [("CYTO", [wrong_candidate])]).best_match
        )
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision(
                    "CYTO", item.name, True, "store-cytotec", correct_query="CYTOTEC"
                )
            )
            with patch("src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB", db_path):
                queries = manual_review_queries(item, ["CYTO"])
                decision = manual_review_match(
                    item,
                    [
                        (
                            queries[0],
                            [
                                {
                                    "storeProductId": "store-cytotec",
                                    "productNameEn": "CYTOTEC 200 MG 14 TABS",
                                }
                            ],
                        )
                    ],
                )

        self.assertEqual(queries, ["CYTOTEC", "CYTO"])
        self.assertIsNotNone(decision)
        self.assertEqual(decision.best_match.data["storeProductId"], "store-cytotec")

    def test_not_matching_decision_filters_rejected_candidate(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            ManualReviewStore(db_path).upsert(
                ManualReviewDecision(
                    "1", "Panadol", False, "store-1", manual_decision="not_matching"
                )
            )
            with patch("src.core.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB", db_path):
                filtered = filter_manual_review_candidates(
                    Item("1", "Panadol", 1),
                    [("Panadol", [{"storeProductId": "store-1"}, {"storeProductId": "store-2"}])],
                )

        self.assertEqual(filtered[0][1], [{"storeProductId": "store-2"}])

class _FakeManualReviewDb:
    def __init__(self) -> None:
        self.lookup_queries: list[tuple[str, tuple]] = []

    def execute_update(self, query, params=()):
        return 1

    def execute_query(self, query, params=()):
        if "information_schema.columns" in query:
            return [("manual_decision",), ("correct_product_name_ar",)]
        self.lookup_queries.append((query, params))
        return [
            ("1", "Panadol", 1, "s1", "approved_match", "Panadol", "", "Panadol", ""),
            ("2", "Cataflam", 1, "s2", "approved_match", "Cataflam", "", "Cataflam", ""),
        ]


if __name__ == "__main__":
    unittest.main()
