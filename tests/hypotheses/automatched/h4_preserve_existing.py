"""H4 regression guard (post-fix): human decisions survive auto-save.

_preserve_existing_decision must keep protecting approved_match /
not_matching rows from being overwritten by auto-save.
"""

from __future__ import annotations

from tests.hypotheses.automatched._framework import (
    HypothesisCase, make_item,
)
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.tawreed.order.tawreed_order_summary_build import (
    _preserve_existing_decision,
)


class H4PreserveExistingTests(HypothesisCase):
    PROBABILITY = 25
    NAME = "H4 preserve-existing guard (regression guard)"

    def test_h4_empty_existing_does_not_block(self) -> None:
        self.assertFalse(_preserve_existing_decision(None))
        self.assertFalse(
            _preserve_existing_decision(
                ManualReviewDecision(
                    item_code="12345", item_name="PANADOL EXTRA 24 TAB",
                    approved=False, manual_decision="needs_correction",
                )
            )
        )

    def test_h4_approved_match_blocks_overwrite(self) -> None:
        existing = ManualReviewDecision(
            item_code="12345", item_name="PANADOL EXTRA 24 TAB",
            approved=True, manual_decision="approved_match",
        )
        self.assertTrue(_preserve_existing_decision(existing))

    def test_h4_human_row_survives_production_flow(self) -> None:
        self.store.upsert(
            ManualReviewDecision(
                item_code=make_item().code, item_name=make_item().name,
                approved=True, correct_store_product_id="HUMAN-1",
                manual_decision="approved_match",
            )
        )
        self.run_production_flow()
        row = self.store.lookup(make_item().code, make_item().name)
        self.assertEqual(row.manual_decision, "approved_match")
        self.assertEqual(row.correct_store_product_id, "HUMAN-1")
