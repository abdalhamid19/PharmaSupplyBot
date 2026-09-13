"""Integration coverage for the LIMITLESS variant identity guard."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from src.core.artifact_run import artifact_run
from src.core.manual_review.manual_review_candidate_store import load_review_candidates
from src.core.manual_review.manual_review_runtime import (
    manual_review_cache_context,
    preload_manual_review_decisions,
)
from src.core.manual_review.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.core.config.config_models import MatchingConfig
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_match_logs import OrderResultSummary
from src.tawreed.matching.tawreed_search_logic import _match_decision
from src.tawreed.order.tawreed_order_summary_build import append_order_item_artifacts


class LimitlessManualReviewIntegrationTests(TestCase):
    """Exercise the seeded decision through preload/cache and artifact handling."""

    def test_stale_auto_match_is_rejected_and_saved_for_manual_review(self) -> None:
        item = Item("92558", "LIMITLESS MILGA MAX 30 TABS", 1)
        man_candidate = {
            "storeProductId": "man-product",
            "productNameEn": "LIMITLESS MAN MAX 30 TABS",
            "availableQuantity": 20,
        }
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "manual-review.sqlite3"
            store = ManualReviewStore(db_path)
            old = ManualReviewDecision(
                item.code,
                item.name,
                True,
                man_candidate["storeProductId"],
                correct_product_name=man_candidate["productNameEn"],
                manual_decision="auto_matched",
                matching_source="tawreed",
            )
            store.upsert(old)

            bot = SimpleNamespace(
                config=SimpleNamespace(matching=MatchingConfig()),
            )
            summary = OrderResultSummary(
                status="no-results",
                reason=(
                    "Product identity conflict: requested LIMITLESS MILGA MAX "
                    "but candidate is LIMITLESS MAN MAX"
                ),
            )
            with patch(
                "src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB",
                db_path,
            ), patch(
                "src.tawreed.order.tawreed_order_summary_build.DEFAULT_MANUAL_REVIEW_DB",
                db_path,
            ):
                cache = preload_manual_review_decisions([item])
                with manual_review_cache_context(cache):
                    decision = _match_decision(
                        bot,
                        item,
                        [(item.name, [man_candidate])],
                    )
                    self.assertIsNone(decision.best_match)

                    with artifact_run("order", "wardany", "limitless-test", root):
                        append_order_item_artifacts(
                            "wardany",
                            item,
                            summary,
                            decision,
                            matching_config=SimpleNamespace(
                                enable_auto_match_re_review_on_fail=False,
                                enable_approved_match_re_review_on_fail=False,
                                enable_auto_save_verified_match=True,
                                manual_review_save_candidate_limit=5,
                            ),
                            database_options={"enabled": False},
                        )

            run_dir = root / "order" / "wardany" / "limitless-test"
            candidates = load_review_candidates(run_dir)
            options = next(iter(candidates.values()))
            self.assertEqual(options[0].name_en, man_candidate["productNameEn"])
            self.assertIn("MILGA", options[0].rejection_reason)
            self.assertIn("MAN", options[0].rejection_reason)

            preserved = ManualReviewStore(db_path).lookup(
                item.code,
                item.name,
                matching_source="tawreed",
            )
            self.assertEqual(preserved, old)


if __name__ == "__main__":
    import unittest

    unittest.main()
