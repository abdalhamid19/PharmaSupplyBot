"""Safety tests for manual-review decisions applied to API candidates."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.core.manual_review_runtime import manual_review_match
from src.core.manual_review_store import ManualReviewDecision
from src.core.utils.excel import Item


class ManualReviewRuntimeApiSafetyTests(unittest.TestCase):
    """Validate saved manual-review matches still require orderable API IDs."""

    def test_name_match_ignores_candidate_without_store_product_id(self) -> None:
        decision = ManualReviewDecision(
            "1",
            "DOLIPRANE 1000 MG 15 TABS",
            True,
            correct_product_name="DOLIPRANE NOVALDOL 1 GM 15 TABS",
        )
        results = [
            (
                "DOLIPRANE",
                [{"productNameEn": "DOLIPRANE NOVALDOL 1 GM 15 TABS"}],
            )
        ]

        with patch(
            "src.core.manual_review_runtime.saved_manual_review_decision",
            return_value=decision,
        ):
            match = manual_review_match(Item("1", decision.item_name, 1), results)

        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
