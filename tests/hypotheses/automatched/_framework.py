"""Hypothesis testing framework for the auto_matched bug.

Each hypothesis module defines PROBABILITY (0-100) and test methods.
The scoring runner at the bottom aggregates results.
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
from src.core.manual_review.manual_review_store import ManualReviewStore  # noqa: E402
from src.core.utils.excel import Item  # noqa: E402
from src.tawreed.order import tawreed_order_summary_build as build  # noqa: E402


class _SummaryStub:
    status = "matched"
    reason = "Accepted best candidate"
    ordered_total_qty = 1
    elapsed_seconds = 0.1
    match_elapsed_seconds = 0.1
    timing_seconds = {}


def make_item() -> Item:
    return Item(code="12345", name="PANADOL EXTRA 24 TAB", qty=1)


def make_candidate() -> dict:
    return {
        "storeProductId": "SP-999",
        "productName": "بانادول اكسترا",
        "productNameEn": "PANADOL EXTRA 24 TAB",
        "companyName": "GSK",
    }


def make_decision(candidate: dict | None = None) -> MatchDecision:
    candidate = candidate or make_candidate()
    return MatchDecision(
        best_match=SearchMatch(
            query="PANADOL EXTRA", row_index=0, score=95.0, data=candidate
        ),
        diagnostics=[],
        final_reason="Accepted best candidate because exact tokens matched.",
    )


def make_config(**overrides) -> MatchingConfig:
    return MatchingConfig(enable_auto_save_verified_match=True, **overrides)


class HypothesisCase(unittest.TestCase):
    """Base class wiring a temp store + patched build.DEFAULT_MANUAL_REVIEW_DB."""

    PROBABILITY: int = 0  # prior probability this hypothesis is the root cause
    NAME: str = "base"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "store.db"
        self.store = ManualReviewStore(self.db_path)
        self._original_db = build.DEFAULT_MANUAL_REVIEW_DB
        build.DEFAULT_MANUAL_REVIEW_DB = self.db_path
        self.addCleanup(self._restore_db)

    def _restore_db(self) -> None:
        build.DEFAULT_MANUAL_REVIEW_DB = self._original_db

    def run_production_flow(self, item=None, decision=None, config=None):
        """Run the exact match-only production save flow once."""
        build.append_order_item_artifacts(
            profile_key="wardany",
            item=item or make_item(),
            summary=_SummaryStub(),
            decision=decision or make_decision(),
            matching_config=config if config is not None else make_config(),
        )

    def auto_rows(self):
        return [
            d for d in self.store.list_decisions()
            if d.manual_decision == "auto_matched"
        ]
