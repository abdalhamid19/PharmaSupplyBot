"""H5: Acceptance order hid missing-storeProductId behind numeric rejection.

_orderable_acceptance only rewrote accepted=True rows. Soft numeric failures
never reached the classic missing-id reason used by not-orderable status.
"""

from __future__ import annotations

import unittest

from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Hypothesis5AcceptanceOrderTests(unittest.TestCase):
    """Score evidence that acceptance pipeline ordering caused the status gap."""

    HYPOTHESIS_SCORE = 0.92

    def test_high_score_oos_row_reports_missing_store_product_id(self) -> None:
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
        self.assertEqual(
            decision.final_reason,
            "Candidate missing orderable storeProductId",
        )

    def test_exact_name_control_still_missing_id(self) -> None:
        decision = explain_best_product_match(
            Item(code="86815", name="LIMITLESS LIPOFERREX 40 MG 30 TABS", qty=1),
            [
                (
                    "LIMITLESS LIPOFERREX 40 MG 30 TABS",
                    [
                        {
                            "productNameEn": "LIMITLESS LIPOFERREX 40 MG 30 TABS",
                            "productName": "ليمتلس",
                            "storeProductId": "",
                        }
                    ],
                )
            ],
        )
        self.assertEqual(
            decision.final_reason,
            "Candidate missing orderable storeProductId",
        )


if __name__ == "__main__":
    unittest.main()
