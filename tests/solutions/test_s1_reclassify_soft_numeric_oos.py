"""S1 scoring: reclassify soft numeric + missing store id as not-orderable.

Recommended primary fix. Preserves strength safety when storeProductId exists.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item
from src.tawreed.tawreed_summary import SummaryStatus


class Solution1ReclassifySoftNumericTests(unittest.TestCase):
    """Score solution S1 against reported items and safety controls."""

    SOLUTION_SCORE = 0.96

    def test_problem_items_become_not_orderable(self) -> None:
        cases = [
            ("29244", "HALOPERIDOL RETARD 1AMP", "HALOPERIDOL RETARD 50 MG / ML I.M.AMP."),
            ("74603", "HAEMOJET AMP", "HAEMOJET 100 MG / 2 ML 6 AMPS."),
        ]
        for code, query, cand in cases:
            with self.subTest(query=query):
                decision = explain_best_product_match(
                    Item(code=code, name=query, qty=1),
                    [
                        (
                            query,
                            [
                                {
                                    "productNameEn": cand,
                                    "productName": cand,
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
                bot = SimpleNamespace(
                    last_order_ai_outcome=None,
                    last_match_decision=decision,
                )
                status = SummaryStatus(bot).skip_status(
                    f"No decisive match found for '{query}' after 4 queries."
                )
                self.assertEqual(status, "not-orderable")

    def test_does_not_auto_order_when_store_id_present(self) -> None:
        decision = explain_best_product_match(
            Item(code="74603", name="HAEMOJET AMP", qty=1),
            [
                (
                    "HAEMOJET AMP",
                    [
                        {
                            "productNameEn": "HAEMOJET 100 MG / 2 ML 6 AMPS.",
                            "productName": "هيموجيت",
                            "storeProductId": "2099814",
                        }
                    ],
                )
            ],
        )
        self.assertIsNone(decision.best_match)
        self.assertIn("unrequested numeric", decision.final_reason.lower())

    def test_weak_sibling_not_reclassified(self) -> None:
        decision = explain_best_product_match(
            Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1),
            [
                (
                    "HALOPERIDOL RETARD 1AMP",
                    [
                        {
                            "productNameEn": "HALOPERIDOL 5 MG / ML I.M. / I.V. 5 AMP.",
                            "productName": "هالوبيريدول",
                            "storeProductId": "",
                        }
                    ],
                )
            ],
        )
        self.assertNotEqual(
            decision.final_reason,
            "Candidate missing orderable storeProductId",
        )


if __name__ == "__main__":
    unittest.main()
