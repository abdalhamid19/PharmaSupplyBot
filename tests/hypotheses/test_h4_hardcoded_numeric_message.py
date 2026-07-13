"""H4: Rejection message hardcoded 'storeProductId' instead of real tokens.

This polluted artifacts and made root-cause analysis harder, but it is a
diagnostic bug, not the main status bug.
"""

from __future__ import annotations

import unittest

from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Hypothesis4HardcodedMessageTests(unittest.TestCase):
    """Score evidence for misleading rejection text."""

    HYPOTHESIS_SCORE = 0.55

    def test_orderable_numeric_rejection_lists_real_tokens(self) -> None:
        decision = explain_best_product_match(
            Item(code="74603", name="HAEMOJET AMP", qty=1),
            [
                (
                    "HAEMOJET AMP",
                    [
                        {
                            "productNameEn": "HAEMOJET 100 MG / 2 ML 6 AMPS.",
                            "productName": "هيموجيت 100 مجم / 2 مل 6 امبول",
                            "storeProductId": "2099814",
                        }
                    ],
                )
            ],
        )
        self.assertIsNone(decision.best_match)
        reason = decision.final_reason.lower()
        self.assertIn("unrequested numeric", reason)
        # Must mention at least one real strength/pack token, not the field name.
        self.assertTrue(any(token in reason for token in ("100", "2", "6")))
        self.assertNotEqual(reason.strip(), "unrequested numeric token: storeproductid")


if __name__ == "__main__":
    unittest.main()
