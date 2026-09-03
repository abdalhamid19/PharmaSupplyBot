"""REPRODUCTION TEST: auto_matched never saved in match-only runs.

User claim (confirmed correct): when running "order run match only", items
should be saved into Saved Corrections (Manual Review Store) as either:
  - approved_match  (if the human corrected the matching), or
  - auto_matched    (if matching succeeded automatically).

Observed behaviour: NO new rows with manual_decision='auto_matched' are
written by the auto-save path, even for perfect matches.

This test proves the claim by calling the exact production flow used by
match-only runs: append_order_item_artifacts() with a perfect accepted match
and a config that enables auto-save. If the store receives a new auto_matched
row, the claim is disproven. If not, the claim is proven.

Expected result BEFORE the fix: FAIL (store stays empty) -> claim proven.
Expected result AFTER the fix: PASS.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config.config_models import MatchingConfig  # noqa: E402
from src.core.matching_types import MatchDecision, SearchMatch  # noqa: E402
from src.core.manual_review.manual_review_store import (  # noqa: E402
    ManualReviewStore,
)
from src.core.utils.excel import Item  # noqa: E402
from src.tawreed.order import tawreed_order_summary_build as build  # noqa: E402


class _SummaryStub:
    """Minimal OrderResultSummary stand-in for a successful match-only run."""

    status = "matched"
    reason = "Accepted best candidate"
    ordered_total_qty = 1
    elapsed_seconds = 0.1
    match_elapsed_seconds = 0.1
    timing_seconds = {}


class ReproductionAutoMatchedNotSavedTests(unittest.TestCase):
    """Prove/disprove: perfect match-only results save nothing as auto_matched."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "manual_review_decisions.db"
        self.store = ManualReviewStore(self.db_path)

        # Patch the store target used inside the production save path.
        self._original_db = build.DEFAULT_MANUAL_REVIEW_DB
        build.DEFAULT_MANUAL_REVIEW_DB = self.db_path
        self.addCleanup(self._restore_db)

        self.item = Item(code="12345", name="PANADOL EXTRA 24 TAB", qty=1)
        self.candidate = {
            "storeProductId": "SP-999",
            "productName": "بانادول اكسترا",
            "productNameEn": "PANADOL EXTRA 24 TAB",
            "companyName": "GSK",
        }
        self.decision = MatchDecision(
            best_match=SearchMatch(
                query="PANADOL EXTRA", row_index=0, score=95.0,
                data=self.candidate,
            ),
            diagnostics=[],
            final_reason="Accepted best candidate because exact tokens matched.",
        )
        self.config = MatchingConfig(enable_auto_save_verified_match=True)

    def _restore_db(self) -> None:
        build.DEFAULT_MANUAL_REVIEW_DB = self._original_db

    def _decisions(self) -> list:
        return self.store.list_decisions()

    def test_perfect_match_only_run_saves_auto_matched_row(self) -> None:
        """Production flow: append_order_item_artifacts on a perfect match."""
        build.append_order_item_artifacts(
            profile_key="wardany",
            item=self.item,
            summary=_SummaryStub(),
            decision=self.decision,
            matching_config=self.config,
        )
        decisions = self._decisions()
        auto = [d for d in decisions if d.manual_decision == "auto_matched"]
        self.assertEqual(
            len(auto), 1,
            "CLAIM CONFIRMED: perfect match-only run saved NO auto_matched row; "
            f"store contains: {[d.manual_decision for d in decisions]}",
        )
        self.assertEqual(auto[0].item_code, "12345")
        self.assertEqual(auto[0].correct_store_product_id, "SP-999")

    def test_truthiness_of_tuple_contract_is_always_true(self) -> None:
        """The runtime helper returns a tuple; bare truthiness is always True."""
        from src.core.manual_review.manual_review_runtime import (
            should_skip_auto_save_verified_match,
        )
        result = should_skip_auto_save_verified_match(self.item, self.candidate, None)
        self.assertIsInstance(result, tuple)
        # The buggy call-site does `if should_skip_...:` — a tuple is always truthy.
        self.assertTrue(bool(result))


if __name__ == "__main__":
    unittest.main()
