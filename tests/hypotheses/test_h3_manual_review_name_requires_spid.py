"""H3: Approved manual-review name match previously required storeProductId.

That made approved_match useless for permanently non-orderable catalog rows
such as HALOPERIDOL RETARD (storeProductId always empty).
"""

from __future__ import annotations

import unittest

from src.core.manual_review.manual_review_runtime import manual_review_match
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.utils.excel import Item


class Hypothesis3ManualReviewStoreIdTests(unittest.TestCase):
    """Score evidence for approved_match not applying on OOS rows."""

    HYPOTHESIS_SCORE = 0.90

    def test_name_match_works_without_store_id_after_fix(self) -> None:
        item = Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1)
        candidate = {
            "productNameEn": "HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
            "productName": "هالوبيريدول ريتارد 50 مجم / مل امبول",
            "storeProductId": "",
        }
        decision = ManualReviewDecision(
            item_code="29244",
            item_name=item.name,
            approved=True,
            correct_store_product_id="",
            correct_product_name="HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
            correct_product_name_ar="هالوبيريدول ريتارد 50 مجم / مل امبول",
            manual_decision="approved_match",
        )
        forced = manual_review_match(item, [(item.name, [candidate])], decision)
        self.assertIsNotNone(forced)
        self.assertIsNotNone(forced.best_match)

    def test_name_match_still_works_with_store_id(self) -> None:
        item = Item(code="74603", name="HAEMOJET AMP", qty=1)
        candidate = {
            "productNameEn": "HAEMOJET 100 MG / 2 ML 6 AMPS.",
            "productName": "هيموجيت 100 مجم / 2 مل 6 امبول",
            "storeProductId": "2099814",
        }
        decision = ManualReviewDecision(
            item_code="74603",
            item_name=item.name,
            approved=True,
            correct_product_name="HAEMOJET 100 MG / 2 ML 6 AMPS.",
            correct_product_name_ar="هيموجيت 100 مجم / 2 مل 6 امبول",
            manual_decision="approved_match",
        )
        forced = manual_review_match(item, [(item.name, [candidate])], decision)
        self.assertIsNotNone(forced)
        self.assertEqual(
            forced.final_reason,
            "Approved by saved manual review (Name match).",
        )


if __name__ == "__main__":
    unittest.main()
