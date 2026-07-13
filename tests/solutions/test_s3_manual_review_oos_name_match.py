"""S3 scoring: allow approved name match without storeProductId, then skip.

Complements S1 for rows that already have human-approved names.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.core.manual_review.manual_review_runtime import manual_review_match
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_search_logic import manual_review_result
from src.tawreed.tawreed_summary import SummaryStatus


class Solution3ManualReviewOosNameMatchTests(unittest.TestCase):
    """Score solution S3 approved-name path for non-orderable products."""

    SOLUTION_SCORE = 0.88

    def test_force_match_then_skip_as_not_orderable(self) -> None:
        item = Item(code="74603", name="HAEMOJET AMP", qty=1)
        candidate = {
            "productNameEn": "HAEMOJET 100 MG / 2 ML 6 AMPS.",
            "productName": "هيموجيت 100 مجم / 2 مل 6 امبول",
            "storeProductId": "",
        }
        review = ManualReviewDecision(
            item_code="74603",
            item_name=item.name,
            approved=True,
            correct_product_name="HAEMOJET 100 MG / 2 ML 6 AMPS.",
            correct_product_name_ar="هيموجيت 100 مجم / 2 مل 6 امبول",
            manual_decision="approved_match",
        )
        forced = manual_review_match(item, [(item.name, [candidate])], review)
        self.assertIsNotNone(forced)
        bot = MagicMock()
        bot.skip_item_exception = RuntimeError
        with self.assertRaises(RuntimeError) as raised:
            manual_review_result(
                bot,
                item,
                started_at=0.0,
                queries=[item.name],
                results=[(item.name, [candidate])],
                review_decision=review,
            )
        status = SummaryStatus(
            SimpleNamespace(last_order_ai_outcome=None, last_match_decision=None)
        ).skip_status(str(raised.exception))
        self.assertEqual(status, "not-orderable")


if __name__ == "__main__":
    unittest.main()
