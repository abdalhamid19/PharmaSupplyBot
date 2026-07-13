"""H2: Correct product is rejected only because storeProductId is missing.

Artifacts show CO AVAZIR EYE OINT. 5 GM score=16.8 (higher than wrong 15.36)
but accepted=False with reason 'Candidate missing orderable storeProductId'.
"""

from __future__ import annotations

import unittest

from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Hypothesis2MissingStoreProductIdTests(unittest.TestCase):
    """Measure evidence for the unorderable-correct-product contributing cause."""

    def test_correct_without_store_id_is_rejected_as_unorderable(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        correct = {
            "productNameEn": "CO AVAZIR EYE OINT. 5 GM",
            "productName": "كو افازير مرهم للعين 5 جم",
            "availableQuantity": 0,
            "productsCount": 0,
        }
        decision = explain_best_product_match(item, [(item.name, [correct])])
        self.assertIsNone(decision.best_match)
        rejected = [d for d in decision.diagnostics if not d.accepted]
        self.assertTrue(rejected)
        self.assertIn(
            "storeProductId",
            rejected[0].rejection_reason,
        )

    def test_correct_with_store_id_is_accepted(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        correct = {
            "productNameEn": "CO AVAZIR EYE OINT. 5 GM",
            "productName": "كو افازير مرهم للعين 5 جم",
            "storeProductId": "3386",
            "availableQuantity": 5,
            "productsCount": 5,
        }
        decision = explain_best_product_match(item, [(item.name, [correct])])
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"],
            "CO AVAZIR EYE OINT. 5 GM",
        )


if __name__ == "__main__":
    unittest.main()
