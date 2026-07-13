"""Regression tests for out-of-stock products misclassified as no-results.

Problem items from production:
- 29244 HALOPERIDOL RETARD 1AMP -> HALOPERIDOL RETARD 50 MG / ML I.M.AMP.
- 74603 HAEMOJET AMP -> HAEMOJET 100 MG / 2 ML 6 AMPS.

Both exist in the catalog without an orderable storeProductId and must become
not-orderable (recognized but unorderable), not no-results.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.core.manual_review.manual_review_helpers import _find_name_match_in_candidates
from src.core.manual_review.manual_review_runtime import manual_review_match
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_search_logic import manual_review_result
from src.tawreed.tawreed_summary import SummaryStatus, _diagnostic_missing_orderable_identity


def _candidate(
    english_name: str,
    arabic_name: str = "",
    store_id: str = "",
    qty: int = 0,
) -> dict[str, object]:
    """Return one Tawreed-style candidate row."""
    data: dict[str, object] = {
        "productNameEn": english_name,
        "productName": arabic_name or english_name,
        "availableQuantity": qty,
        "productsCount": qty,
    }
    if store_id:
        data["storeProductId"] = store_id
    return data


class HaloperidolHaemojetNoResultsTests(unittest.TestCase):
    """Lock the reported false no-results cases to the not-orderable path."""

    PROBLEM_CASES = (
        (
            "29244",
            "HALOPERIDOL RETARD 1AMP",
            "HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
            "هالوبيريدول ريتارد 50 مجم / مل امبول",
        ),
        (
            "74603",
            "HAEMOJET AMP",
            "HAEMOJET 100 MG / 2 ML 6 AMPS.",
            "هيموجيت 100 مجم / 2 مل 6 امبول",
        ),
    )

    def test_auto_match_does_not_order_out_of_stock_rows(self) -> None:
        """Out-of-stock catalog rows must never become actionable best_match."""
        for code, item_name, cand_en, cand_ar in self.PROBLEM_CASES:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(cand_en, cand_ar, store_id="")])],
                )
                self.assertIsNone(decision.best_match)
                self.assertTrue(decision.diagnostics)
                self.assertIn(
                    "storeProductId",
                    decision.final_reason,
                )

    def test_out_of_stock_rows_classify_as_not_orderable(self) -> None:
        """Diagnostics for the correct product must flip status to not-orderable."""
        for code, item_name, cand_en, cand_ar in self.PROBLEM_CASES:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(cand_en, cand_ar, store_id="")])],
                )
                best = max(decision.diagnostics, key=lambda d: d.score)
                self.assertTrue(_diagnostic_missing_orderable_identity(best))
                bot = SimpleNamespace(
                    last_order_ai_outcome=None,
                    last_match_decision=decision,
                )
                status = SummaryStatus(bot).skip_status(
                    f"No decisive match found for '{item_name}' after 4 queries."
                )
                self.assertEqual(status, "not-orderable")

    def test_orderable_control_still_needs_strength_for_auto_match(self) -> None:
        """When storeProductId exists, missing strength must still block auto-order."""
        decision = explain_best_product_match(
            Item(code="74603", name="HAEMOJET AMP", qty=1),
            [
                (
                    "HAEMOJET AMP",
                    [
                        _candidate(
                            "HAEMOJET 100 MG / 2 ML 6 AMPS.",
                            store_id="2099814",
                            qty=5,
                        )
                    ],
                )
            ],
        )
        self.assertIsNone(decision.best_match)
        self.assertIn("unrequested numeric", decision.final_reason.lower())

    def test_limitless_style_exact_name_still_not_orderable(self) -> None:
        """Exact-name missing-id rows keep the classic not-orderable path."""
        decision = explain_best_product_match(
            Item(code="86815", name="LIMITLESS LIPOFERREX 40 MG 30 TABS", qty=1),
            [
                (
                    "LIMITLESS LIPOFERREX 40 MG 30 TABS",
                    [
                        _candidate(
                            "LIMITLESS LIPOFERREX 40 MG 30 TABS",
                            store_id="",
                        )
                    ],
                )
            ],
        )
        self.assertIsNone(decision.best_match)
        self.assertIn(
            "Candidate missing orderable storeProductId",
            decision.final_reason,
        )
        self.assertTrue(
            _diagnostic_missing_orderable_identity(decision.diagnostics[0])
        )

    def test_approved_manual_review_name_match_without_store_id(self) -> None:
        """Saved approved names must recognize non-orderable catalog rows."""
        for code, item_name, cand_en, cand_ar in self.PROBLEM_CASES:
            with self.subTest(item_name=item_name):
                item = Item(code=code, name=item_name, qty=1)
                candidate = _candidate(cand_en, cand_ar, store_id="")
                decision = ManualReviewDecision(
                    item_code=code,
                    item_name=item_name,
                    approved=True,
                    correct_store_product_id="",
                    correct_product_name=cand_en,
                    correct_product_name_ar=cand_ar,
                    manual_decision="approved_match",
                )
                forced = manual_review_match(
                    item, [(item_name, [candidate])], decision
                )
                self.assertIsNotNone(forced)
                self.assertIsNotNone(forced.best_match)
                self.assertIn("not orderable", forced.final_reason.lower())

    def test_manual_review_result_skips_as_not_orderable(self) -> None:
        """Forced approved name match without store id must skip as not-orderable."""
        item = Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1)
        candidate = _candidate(
            "HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
            "هالوبيريدول ريتارد 50 مجم / مل امبول",
            store_id="",
        )
        review = ManualReviewDecision(
            item_code="29244",
            item_name=item.name,
            approved=True,
            correct_product_name="HALOPERIDOL RETARD 50 MG / ML I.M.AMP.",
            correct_product_name_ar="هالوبيريدول ريتارد 50 مجم / مل امبول",
            manual_decision="approved_match",
        )
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
        self.assertIn("not orderable", str(raised.exception).lower())
        self.assertIn("storeproductid", str(raised.exception).lower())
        status = SummaryStatus(
            SimpleNamespace(last_order_ai_outcome=None, last_match_decision=None)
        ).skip_status(str(raised.exception))
        self.assertEqual(status, "not-orderable")

    def test_wrong_strength_sibling_stays_below_not_orderable_floor(self) -> None:
        """Weaker sibling SKUs must not steal not-orderable recognition."""
        decision = explain_best_product_match(
            Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1),
            [
                (
                    "HALOPERIDOL RETARD 1AMP",
                    [
                        _candidate(
                            "HALOPERIDOL 5 MG / ML I.M. / I.V. 5 AMP.",
                            store_id="",
                        )
                    ],
                )
            ],
        )
        best = decision.diagnostics[0]
        self.assertLess(best.score, 9.0)
        # After reclassification only high-score soft rows become not-orderable.
        if "missing orderable" not in best.rejection_reason.lower():
            self.assertFalse(_diagnostic_missing_orderable_identity(best))


if __name__ == "__main__":
    unittest.main()
