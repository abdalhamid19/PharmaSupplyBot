"""Post-fix verification: auto_matched saving works end-to-end.

Covers the full production save path after the S2 fix:
  1. Healthy match-only run  -> auto_matched row persisted.
  2. Conflict rejection      -> skipped (protection retained).
  3. Manufacturer flag on    -> heuristic conflict blocks save (opt-in works).
  4. Human approved_match    -> survives auto-save overwrite.
  5. Forced 999 match        -> not re-saved.
  6. Reviewable status       -> goes to review, not auto-save.
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
from src.core.matching_types import (  # noqa: E402
    CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown, SearchMatch,
)
from src.core.manual_review.manual_review_store import (  # noqa: E402
    ManualReviewDecision, ManualReviewStore,
)
from src.core.utils.excel import Item  # noqa: E402
from src.tawreed.order import tawreed_order_summary_build as build  # noqa: E402


class _SummaryStub:
    status = "matched"
    reason = "Accepted best candidate"
    ordered_total_qty = 1
    elapsed_seconds = 0.1
    match_elapsed_seconds = 0.1
    timing_seconds = {}


class _ReviewSummaryStub(_SummaryStub):
    status = "no-results"


def _item() -> Item:
    return Item(code="12345", name="PANADOL EXTRA 24 TAB", qty=1)


def _candidate() -> dict:
    return {
        "storeProductId": "SP-999",
        "productName": "بانادول اكسترا",
        "productNameEn": "PANADOL EXTRA 24 TAB",
        "companyName": "GSK",
    }


def _diagnostic(rejection_reason: str = "") -> CandidateMatchDiagnostic:
    breakdown = MatchScoreBreakdown(
        sequence_score=0.0, overlap_score=0.0, numeric_overlap=0.0,
        exact_bonus=0.0, availability_bonus=0.0, critical_penalty=0.0,
        extra_token_penalty=0.0, semantic_penalty=0.0, total_score=95.0,
    )
    return CandidateMatchDiagnostic(
        query="PANADOL EXTRA", row_index=0, score=95.0,
        sort_key=(95.0, 0, 0.0, 0, 0, 0),
        accepted=not rejection_reason,
        accepted_reason="" if rejection_reason else "high overlap",
        rejection_reason=rejection_reason,
        breakdown=breakdown, candidate=_candidate(),
    )


def _decision(rejection_reason: str = "", score: float = 95.0,
              final_reason: str = "Accepted best candidate because high overlap.") -> MatchDecision:
    return MatchDecision(
        best_match=SearchMatch(
            query="PANADOL EXTRA", row_index=0, score=score, data=_candidate()
        ),
        diagnostics=[_diagnostic(rejection_reason)],
        final_reason=final_reason,
    )


def _real_conflict_item() -> Item:
    """Item naming a curated manufacturer (ORCHIDIA) explicitly."""
    return Item(code="77777", name="METHYL FOLATE 30 CAP ORCHIDIA", qty=1)


def _real_conflict_candidate() -> dict:
    """Candidate whose explicit companyName is a different curated maker."""
    return {
        "storeProductId": "SP-777",
        "productName": "ميثيل فولات",
        "productNameEn": "METHYL FOLATE ORA 30 CAPS",
        "companyName": "ORA",
    }


def _real_conflict_decision() -> MatchDecision:
    breakdown = MatchScoreBreakdown(
        sequence_score=0.0, overlap_score=0.0, numeric_overlap=0.0,
        exact_bonus=0.0, availability_bonus=0.0, critical_penalty=0.0,
        extra_token_penalty=0.0, semantic_penalty=0.0, total_score=95.0,
    )
    diagnostic = CandidateMatchDiagnostic(
        query="METHYL FOLATE", row_index=0, score=95.0,
        sort_key=(95.0, 0, 0.0, 0, 0, 0),
        accepted=True, accepted_reason="high overlap", rejection_reason="",
        breakdown=breakdown, candidate=_real_conflict_candidate(),
    )
    return MatchDecision(
        best_match=SearchMatch(
            query="METHYL FOLATE", row_index=0, score=95.0,
            data=_real_conflict_candidate(),
        ),
        diagnostics=[diagnostic],
        final_reason="Accepted best candidate because high overlap.",
    )


class PostFixAutoMatchedSavingTests(unittest.TestCase):
    """Full save-path verification after the tuple-unpacking + gating fix."""

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

    def _run_flow(self, decision, config=None, summary=None, item=None) -> None:
        build.append_order_item_artifacts(
            profile_key="wardany",
            item=item or _item(),
            summary=summary or _SummaryStub(),
            decision=decision,
            matching_config=config if config is not None else MatchingConfig(),
        )

    def _auto_rows(self):
        return [
            d for d in self.store.list_decisions()
            if d.manual_decision == "auto_matched"
        ]

    def test_1_healthy_match_saved_as_auto_matched(self) -> None:
        self._run_flow(_decision())
        rows = self._auto_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].correct_store_product_id, "SP-999")
        self.assertEqual(rows[0].item_code, "12345")

    def test_2_conflict_rejection_still_blocks_save(self) -> None:
        self._run_flow(
            _decision(rejection_reason="Semantic mismatch: brand conflict")
        )
        self.assertEqual(len(self.store.list_decisions()), 0)

    def test_3_manufacturer_flag_opt_in_blocks_real_conflict(self) -> None:
        """Opt-in check blocks a genuine curated-vs-explicit maker conflict.

        ORCHIDIA (named in the item) vs companyName 'ORA' — both are curated
        manufacturers, so this is a real conflict, not a phantom one.
        """
        config = MatchingConfig(enable_manufacturer_check=True)
        self._run_flow(
            _real_conflict_decision(), config=config, item=_real_conflict_item()
        )
        self.assertEqual(len(self.store.list_decisions()), 0)

    def test_3b_manufacturer_flag_on_does_not_block_phantom_conflict(self) -> None:
        """'PANADOL EXTRA' no longer yields a phantom 'EXTRA' manufacturer.

        Before the explicit-fields-only fix, enabling the check blocked this
        healthy match because 'EXTRA' was read as the item's manufacturer and
        compared against companyName 'GSK'.
        """
        config = MatchingConfig(enable_manufacturer_check=True)
        self._run_flow(_decision(), config=config)
        self.assertEqual(len(self._auto_rows()), 1)

    def test_4_human_approved_match_survives(self) -> None:
        self.store.upsert(
            ManualReviewDecision(
                item_code="12345", item_name="PANADOL EXTRA 24 TAB",
                approved=True, correct_store_product_id="HUMAN-1",
                manual_decision="approved_match",
            )
        )
        self._run_flow(_decision())
        row = self.store.lookup("12345", "PANADOL EXTRA 24 TAB")
        self.assertEqual(row.manual_decision, "approved_match")
        self.assertEqual(row.correct_store_product_id, "HUMAN-1")

    def test_5_forced_999_match_not_re_saved(self) -> None:
        """999 score + 'Approved by saved manual review' = store-served match;
        re-saving it would duplicate rows the store itself produced."""
        self._run_flow(
            _decision(
                score=999.0,
                final_reason="Approved by saved manual review.",
            )
        )
        self.assertEqual(len(self.store.list_decisions()), 0)

    def test_6_reviewable_status_goes_to_review_not_save(self) -> None:
        self._run_flow(_decision(), summary=_ReviewSummaryStub())
        self.assertEqual(len(self._auto_rows()), 0)

    def test_7_flag_off_disables_auto_save_entirely(self) -> None:
        config = MatchingConfig(enable_auto_save_verified_match=False)
        self._run_flow(_decision(), config=config)
        self.assertEqual(len(self.store.list_decisions()), 0)


if __name__ == "__main__":
    unittest.main()
