"""H3 regression guard (post-fix): review routing semantics unchanged.

Healthy 'matched' items still reach auto-save; reviewable statuses still
route to manual review instead.
"""

from __future__ import annotations

from tests.hypotheses.automatched._framework import HypothesisCase, make_item
from src.core.ordering.order_run_artifact_rows import manual_review_required


class _Summary:
    def __init__(self, status: str) -> None:
        self.status = status


class H3ManualReviewRequiredTests(HypothesisCase):
    PROBABILITY = 40
    NAME = "H3 manual-review routing (regression guard)"

    def test_h3_healthy_match_not_routed_to_review(self) -> None:
        self.assertFalse(manual_review_required(make_item(), "matched", None))

    def test_h3_reviewable_status_routed_to_review(self) -> None:
        self.assertTrue(
            manual_review_required(make_item(), "manual-review-required", None)
        )
        self.assertTrue(manual_review_required(make_item(), "no-results", None))

    def test_h3_review_path_saves_no_auto_matched(self) -> None:
        from src.core.config.config_models import MatchingConfig
        from src.tawreed.order import tawreed_order_summary_build as build
        build.append_order_item_artifacts(
            profile_key="wardany",
            item=make_item(),
            summary=_Summary("no-results"),
            decision=None,
            matching_config=MatchingConfig(),
        )
        self.assertEqual(len(self.auto_rows()), 0)
