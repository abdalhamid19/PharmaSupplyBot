"""H6 regression guard (post-fix): store persistence works reliably.

Direct store round-trips must keep working — guards the silent-write-failure
hypothesis stays rejected.
"""

from __future__ import annotations

from src.core.manual_review.manual_review_store import ManualReviewDecision
from tests.hypotheses.automatched._framework import HypothesisCase, make_item


class H6DbWriteFailureTests(HypothesisCase):
    PROBABILITY = 5
    NAME = "H6 DB write failure (regression guard)"

    def test_h6_store_upsert_roundtrip_works(self) -> None:
        decision = ManualReviewDecision(
            item_code=make_item().code,
            item_name=make_item().name,
            approved=True,
            correct_store_product_id="SP-1",
            manual_decision="auto_matched",
        )
        self.store.upsert(decision)
        rows = self.auto_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].correct_store_product_id, "SP-1")

    def test_h6_upsert_batch_roundtrip_works(self) -> None:
        decision = ManualReviewDecision(
            item_code="X1", item_name="TEST ITEM", approved=True,
            manual_decision="auto_matched",
        )
        self.store.upsert_batch([decision])
        self.assertEqual(len(self.auto_rows()), 1)
