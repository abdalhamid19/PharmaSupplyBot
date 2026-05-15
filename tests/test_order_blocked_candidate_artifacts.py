"""Tests for blocked AI candidate order summary fields."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.core.matching_models import MatchDecision
from src.core.order_ai_matching import OrderAiOutcome
from src.core.order_run_artifact_rows import manual_review_row, order_item_summary_row
from src.core.utils.excel import Item


class OrderBlockedCandidateArtifactsTests(unittest.TestCase):
    """Validate artifact rows for AI matches missing storeProductId."""

    def test_missing_store_product_id_maps_to_unavailable_with_candidate_fields(self):
        """A locally blocked AI candidate remains visible but not actionable."""
        row = order_item_summary_row(
            Item("28406", "BEBELAC AR MILK", 1),
            SimpleNamespace(
                status="manual-review-required",
                reason="No decisive match found",
            ),
            MatchDecision(None, [], "none"),
            self._missing_store_id_outcome(),
        )
        self.assertEqual(row["status"], "matched-but-unavailable")
        self.assertEqual(row["manual_review_category"], "candidate_not_orderable")
        self.assertEqual(row["candidate_safety_reason"], "missing storeProductId")
        self.assertEqual(row["matched"], False)
        self.assertEqual(row["matched_product_name_en"], "BEBELAC AR MILK 400 GM")
        self.assertEqual(row["matched_product_id"], 1748)
        self.assertEqual(row["blocked_candidate_name_ar"], "بيبيلاك ايه ار لبن 400 جم")
        self.assertEqual(row["blocked_candidate_available_quantity"], 0)

    def test_manual_review_row_uses_effective_status_for_missing_store_id(self):
        """Manual review rows carry the effective unavailable status."""
        row = manual_review_row(
            Item("16763", "AMRIZOLE N SUPP", 1),
            SimpleNamespace(
                status="manual-review-required",
                reason="No decisive match found",
            ),
            MatchDecision(None, [], "none"),
            self._missing_store_id_outcome(),
        )
        self.assertEqual(row["status"], "matched-but-unavailable")
        self.assertEqual(row["manual_review_reason_code"], "ai_rejected")
        self.assertEqual(row["correct_store_product_id"], "")

    @staticmethod
    def _missing_store_id_outcome() -> OrderAiOutcome:
        search_result = {
            "record": {
                "product_name_en": "BEBELAC AR MILK 400 GM",
                "product_name_ar": "بيبيلاك ايه ار لبن 400 جم",
                "store_product_id": "",
                "_query": "BEBELAC AR MILK",
                "_raw": {
                    "productNameEn": "BEBELAC AR MILK 400 GM",
                    "productName": "بيبيلاك ايه ار لبن 400 جم",
                    "productId": 1748,
                    "storeProductId": None,
                    "availableQuantity": 0,
                    "salePrice": 430.0,
                },
            },
            "confidence": 0.99,
            "reason": "Exact match on brand and product name",
        }
        return OrderAiOutcome(
            MatchDecision(None, [], "none"),
            "ai_rejected",
            "AI search candidate failed local safety: missing storeProductId",
            0.99,
            True,
            search_result=search_result,
        )


if __name__ == "__main__":
    unittest.main()
