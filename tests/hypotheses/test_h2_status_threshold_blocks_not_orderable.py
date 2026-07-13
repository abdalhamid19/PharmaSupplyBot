"""H2: Status classifier required score>=12 or exact missing-id reason.

Production scores for HALOPERIDOL/HAEMOJET are ~9.9-10.1, so they never
crossed the not-orderable floor and fell back to no-results.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item
from src.tawreed.tawreed_summary import SummaryStatus, _diagnostic_missing_orderable_identity


class Hypothesis2StatusThresholdTests(unittest.TestCase):
    """Score evidence that status mapping, not search, produced no-results."""

    HYPOTHESIS_SCORE = 0.98

    def test_problem_scores_are_below_legacy_medium_threshold(self) -> None:
        cases = [
            ("HALOPERIDOL RETARD 1AMP", "HALOPERIDOL RETARD 50 MG / ML I.M.AMP."),
            ("HAEMOJET AMP", "HAEMOJET 100 MG / 2 ML 6 AMPS."),
        ]
        for query, cand in cases:
            with self.subTest(query=query):
                decision = explain_best_product_match(
                    Item(code="x", name=query, qty=1),
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
                score = decision.diagnostics[0].score
                self.assertLess(score, 12.0)
                self.assertGreaterEqual(score, 9.0)

    def test_status_is_not_orderable_after_fix(self) -> None:
        decision = explain_best_product_match(
            Item(code="74603", name="HAEMOJET AMP", qty=1),
            [
                (
                    "HAEMOJET AMP",
                    [
                        {
                            "productNameEn": "HAEMOJET 100 MG / 2 ML 6 AMPS.",
                            "productName": "هيموجيت 100 مجم / 2 مل 6 امبول",
                            "storeProductId": "",
                        }
                    ],
                )
            ],
        )
        best = decision.diagnostics[0]
        self.assertTrue(_diagnostic_missing_orderable_identity(best))
        bot = SimpleNamespace(last_order_ai_outcome=None, last_match_decision=decision)
        status = SummaryStatus(bot).skip_status(
            "No decisive match found for 'HAEMOJET AMP' after 4 queries."
        )
        self.assertEqual(status, "not-orderable")


if __name__ == "__main__":
    unittest.main()
