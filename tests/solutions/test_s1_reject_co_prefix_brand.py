"""S1 scoring: reject brand when one side is exactly CO + the other.

Best surgical fix for CO_AVAZIR vs AVAZIR without broad fuzzy threshold churn.
"""

from __future__ import annotations

import unittest

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_brand import (
    _co_prefixed_brand_mismatch,
)
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)
from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Solution1CoPrefixBrandTests(unittest.TestCase):
    """Score solution S1 against the reported item and safe controls."""

    def test_helper_detects_co_prefix(self) -> None:
        self.assertTrue(_co_prefixed_brand_mismatch("COAVAZIR", "AVAZIR"))
        self.assertTrue(_co_prefixed_brand_mismatch("AVAZIR", "COAVAZIR"))
        self.assertFalse(_co_prefixed_brand_mismatch("COAVAZIR", "COAVAZIR"))
        self.assertFalse(_co_prefixed_brand_mismatch("LILI", "LILIOX"))

    def test_rejects_wrong_avazir_ointment(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        wrong = {
            "productNameEn": "AVAZIR 0.3 % EYE OINT. 5 GM",
            "productName": "",
            "storeProductId": "1450",
            "availableQuantity": 7,
        }
        decision = explain_best_product_match(item, [(item.name, [wrong])])
        self.assertIsNone(decision.best_match)

    def test_still_accepts_correct_co_avazir(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        correct = {
            "productNameEn": "CO AVAZIR EYE OINT. 5 GM",
            "productName": "",
            "storeProductId": "3386",
            "availableQuantity": 5,
        }
        decision = explain_best_product_match(item, [(item.name, [correct])])
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"],
            "CO AVAZIR EYE OINT. 5 GM",
        )

    def test_known_safe_containment_still_ok(self) -> None:
        ok, reason = components_match(
            parse_drug("AMIKACIN 500MG VIAL"),
            parse_drug("AMIKACIN AMOUN 500 MG / 2 ML VIAL"),
        )
        self.assertTrue(ok, reason)


if __name__ == "__main__":
    unittest.main()
