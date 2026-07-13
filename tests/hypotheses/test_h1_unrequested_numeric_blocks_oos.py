"""H1: Unrequested numeric tokens block recognition of out-of-stock SKUs.

Score meaning: how strongly this hypothesis explains production no-results.
"""

from __future__ import annotations

import unittest

from src.core.matching.product_matching import explain_best_product_match
from src.core.matching.product_matching_acceptance import _extra_numeric_tokens
from src.core.utils.excel import Item


class Hypothesis1UnrequestedNumericTests(unittest.TestCase):
    """Measure evidence that soft numeric rejection is the first blocker."""

    HYPOTHESIS_SCORE = 0.95

    def test_extra_numeric_tokens_are_present(self) -> None:
        cases = [
            (
                "HALOPERIDOL RETARD 1AMP",
                "HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
                {"50"},
            ),
            (
                "HAEMOJET AMP",
                "HAEMOJET 100 MG / 2 ML 6 AMPS.",
                {"100", "2", "6"},
            ),
        ]
        for query, cand_name, expected in cases:
            with self.subTest(query=query):
                candidate = {
                    "productNameEn": cand_name,
                    "productName": cand_name,
                    "storeProductId": "",
                }
                self.assertEqual(_extra_numeric_tokens(query, candidate), expected)

    def test_decision_is_rejected_for_numeric_or_missing_id(self) -> None:
        decision = explain_best_product_match(
            Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1),
            [
                (
                    "HALOPERIDOL RETARD 1AMP",
                    [
                        {
                            "productNameEn": "HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
                            "productName": "هالوبيريدول ريتارد 50 مجم / مل امبول",
                            "storeProductId": "",
                        }
                    ],
                )
            ],
        )
        self.assertIsNone(decision.best_match)
        # Before fix: unrequested numeric. After fix: missing storeProductId.
        reason = decision.final_reason.lower()
        self.assertTrue(
            "unrequested numeric" in reason or "storeproductid" in reason,
            reason,
        )


if __name__ == "__main__":
    unittest.main()
