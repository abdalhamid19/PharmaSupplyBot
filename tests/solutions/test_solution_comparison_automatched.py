"""SOLUTION COMPARISON TESTS for the auto_matched never-saved bug.

Three candidate solutions are compared:

S1 (minimal): unpack the tuple at the call site in
    _auto_save_verified_match: `skip, _ = should_skip_...` then `if skip: return`.
    Fixes the dead branch but keeps the broken manufacturer extractor, so many
    legitimate matches (e.g. 'PANADOL EXTRA' + companyName GSK) would STILL be
    skipped as 'conflict' -> saves far fewer rows than intended.

S2 (tuple + guard fix, RECOMMENDED): unpack the tuple AND gate the
    manufacturer-conflict check behind enable_manufacturer_check (the existing
    MatchingConfig flag, default False). The helper then only rejects on
    explicit conflict-related rejection_reason strings. Saves all healthy
    matches while retaining protection against genuinely conflicting saves
    when the user opts in.

S3 (conservative): revert the safety check entirely (delete the guard call).
    Restores pre-3d3191c behaviour but loses the rejection-reason protection
    the guard was meant to add.

Scoring dimensions:
  - saves_auto_matched      : healthy match persisted?      (weight 3)
  - conflict_protected      : conflict match still blocked? (weight 2)
  - reviewable_status_safe  : no rows for reviewable items? (weight 2)
  - human_decision_preserved: approved_match not overwritten (weight 2)
  - no_false_rejections     : brand-vs-ingredient names not falsely skipped (weight 3)
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config.config_models import MatchingConfig  # noqa: E402
from src.core.matching_types import MatchDecision, SearchMatch  # noqa: E402
from src.core.manual_review.manual_review_store import (  # noqa: E402
    ManualReviewDecision, ManualReviewStore,
)
from src.core.utils.excel import Item  # noqa: E402
from src.tawreed.order import tawreed_order_summary_build as build  # noqa: E402
from src.core.manual_review.manual_review_helpers import (  # noqa: E402
    should_skip_auto_save,
)


class _SummaryStub:
    status = "matched"
    reason = "Accepted best candidate"
    ordered_total_qty = 1
    elapsed_seconds = 0.1
    match_elapsed_seconds = 0.1
    timing_seconds = {}


def healthy_item() -> Item:
    return Item(code="12345", name="PANADOL EXTRA 24 TAB", qty=1)


def healthy_candidate() -> dict:
    return {
        "storeProductId": "SP-999",
        "productName": "بانادول اكسترا",
        "productNameEn": "PANADOL EXTRA 24 TAB",
        "companyName": "GSK",
    }


def healthy_decision() -> MatchDecision:
    return MatchDecision(
        best_match=SearchMatch(
            query="PANADOL EXTRA", row_index=0, score=95.0,
            data=healthy_candidate(),
        ),
        diagnostics=[],
        final_reason="Accepted best candidate because exact tokens matched.",
    )


def conflict_decision() -> MatchDecision:
    """Best diagnostic carries an explicit conflict-related rejection reason.

    Mirrors production: MatchDecision has NO rejection_reason attribute; the
    signal lives on the best CandidateMatchDiagnostic.
    """
    from src.core.matching_types import CandidateMatchDiagnostic, MatchScoreBreakdown

    breakdown = MatchScoreBreakdown(
        sequence_score=0.0, overlap_score=0.0, numeric_overlap=0.0,
        exact_bonus=0.0, availability_bonus=0.0, critical_penalty=0.0,
        extra_token_penalty=0.0, semantic_penalty=10.0, total_score=95.0,
    )
    diagnostic = CandidateMatchDiagnostic(
        query="PANADOL EXTRA", row_index=0, score=95.0,
        sort_key=(95.0, 0, 0.0, 0, 0, 0),
        accepted=True, accepted_reason="high overlap",
        rejection_reason="Semantic mismatch: brand conflict",
        breakdown=breakdown, candidate=healthy_candidate(),
    )
    return MatchDecision(
        best_match=SearchMatch(
            query="PANADOL EXTRA", row_index=0, score=95.0,
            data=healthy_candidate(),
        ),
        diagnostics=[diagnostic],
        final_reason="Accepted best candidate because high overlap.",
    )


# ============================================================================
# Solution implementations (monkeypatched variants of the production flow)
# ============================================================================


def _decision_rejection_reason(decision) -> str | None:
    """Extract a rejection signal the way production should: best diagnostic.

    MatchDecision has no rejection_reason attribute of its own; the real
    signal lives on the winning CandidateMatchDiagnostic.
    """
    diagnostics = getattr(decision, "diagnostics", None) or []
    best = max(diagnostics, key=lambda d: d.score, default=None)
    return getattr(best, "rejection_reason", None) if best else None


def _base_auto_save(item, decision, skip_fn) -> None:
    """Shared skeleton mirroring _auto_save_verified_match with injectable guard."""
    if not decision or not decision.best_match:
        return
    match = decision.best_match
    if match.score == 999.0 and "Approved by saved manual review" in (
        decision.final_reason or ""
    ):
        return
    skip, _reason = skip_fn(
        item, match.data, _decision_rejection_reason(decision)
    )
    if skip:
        return
    store = ManualReviewStore(build.DEFAULT_MANUAL_REVIEW_DB)
    existing = store.lookup(item.code, item.name)
    if existing and existing.manual_decision in ("approved_match", "not_matching"):
        return
    store.upsert(
        ManualReviewDecision(
            item_code=item.code, item_name=item.name, approved=True,
            correct_store_product_id="SP-999",
            manual_decision="auto_matched", correct_query="",
        )
    )


def s1_minimal_skip_fn(item, candidate, rejection_reason):
    """S1: keep current helper semantics (manufacturer check always on)."""
    return should_skip_auto_save(item, candidate, rejection_reason)


def s2_gated_skip_fn(item, candidate, rejection_reason):
    """S2: manufacturer check only when enable_manufacturer_check is on.

    Protection retained: explicit conflict-related rejection_reason strings
    still block the save (the rejection already happened upstream).
    """
    config = getattr(s2_gated_skip_fn, "_config", None)
    if rejection_reason:
        rejection_lower = rejection_reason.lower()
        conflict_keywords = ["conflict", "manufacturer", "brand", "semantic"]
        if any(keyword in rejection_lower for keyword in conflict_keywords):
            return True, f"Conflict-related rejection: {rejection_reason}"
    skip, reason = should_skip_auto_save(item, candidate, None)
    if skip and reason and "Manufacturer conflict" in reason:
        if not (config and getattr(config, "enable_manufacturer_check", False)):
            return False, reason + " (manufacturer check disabled; not blocking)"
    return skip, reason


def s3_no_guard_skip_fn(item, candidate, rejection_reason):
    """S3: guard removed entirely."""
    return False, "guard disabled"


# ============================================================================
# Test case
# ============================================================================


class _SolutionCase(unittest.TestCase):
    """Runs the five scoring criteria against one solution variant."""

    SOLUTION_NAME = "?"

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

    # -- criterion 1: saves healthy match as auto_matched -------------------
    def criterion_saves_auto_matched(self) -> bool:
        self.store.upsert_batch([])  # ensure empty
        _base_auto_save(healthy_item(), healthy_decision(), self._skip_fn())
        rows = [
            d for d in self.store.list_decisions()
            if d.manual_decision == "auto_matched"
        ]
        return len(rows) == 1

    # -- criterion 2: conflict-related rejection still blocks ---------------
    def criterion_conflict_protected(self) -> bool:
        _base_auto_save(healthy_item(), conflict_decision(), self._skip_fn())
        rows = self.store.list_decisions()
        return len(rows) == 0

    # -- criterion 3: human approved_match survives -------------------------
    def criterion_human_decision_preserved(self) -> None:
        self.store.upsert(
            ManualReviewDecision(
                item_code=healthy_item().code,
                item_name=healthy_item().name,
                approved=True, correct_store_product_id="HUMAN-1",
                manual_decision="approved_match",
            )
        )
        _base_auto_save(healthy_item(), healthy_decision(), self._skip_fn())
        row = self.store.lookup(healthy_item().code, healthy_item().name)
        self.assertEqual(row.correct_store_product_id, "HUMAN-1")
        self.assertEqual(row.manual_decision, "approved_match")

    # -- criterion 4: false-rejection rate on brand-like names --------------
    def criterion_no_false_rejections(self) -> None:
        """Names whose last token looks like a 'manufacturer' must not block."""
        skipped = 0
        cases = [
            ("12345", "PANADOL EXTRA 24 TAB", "GSK"),
            ("80838", "CO AVAZIR 5GM EYE OINTMENT", "CID"),
            ("45413", "ABIMOL EXTRA 20 TAB.", "GLAXO"),
        ]
        for code, name, company in cases:
            item = Item(code=code, name=name, qty=1)
            candidate = {
                "storeProductId": "SP-X", "productNameEn": name,
                "productName": name, "companyName": company,
            }
            skip, _ = self._skip_fn()(item, candidate, None)
            if skip:
                skipped += 1
        self.assertEqual(
            skipped, 0,
            f"{self.SOLUTION_NAME}: {skipped}/3 healthy matches falsely skipped",
        )

    def _skip_fn(self):
        raise NotImplementedError


class S1MinimalTests(_SolutionCase):
    SOLUTION_NAME = "S1-minimal (unpack tuple only)"

    def _skip_fn(self):
        return s1_minimal_skip_fn

    def test_s1_scores(self) -> None:
        self.criterion_human_decision_preserved()
        # S1 still falsely rejects healthy matches due to broken extractor:
        saved = self._try_save_healthy()
        self.assertFalse(
            saved, "S1 documented limitation: healthy match still skipped"
        )

    def _try_save_healthy(self) -> bool:
        before = len(self.store.list_decisions())
        _base_auto_save(healthy_item(), healthy_decision(), self._skip_fn())
        return len(self.store.list_decisions()) > before


class S2GatedTests(_SolutionCase):
    SOLUTION_NAME = "S2-gated (recommended)"

    def _skip_fn(self):
        s2_gated_skip_fn._config = MatchingConfig()  # manufacturer_check=False
        return s2_gated_skip_fn

    def test_s2_saves_healthy_match(self) -> None:
        self.assertTrue(self.criterion_saves_auto_matched())

    def test_s2_conflict_protected(self) -> None:
        self.assertTrue(self.criterion_conflict_protected())

    def test_s2_human_decision_preserved(self) -> None:
        self.criterion_human_decision_preserved()

    def test_s2_no_false_rejections(self) -> None:
        self.criterion_no_false_rejections()


class S3NoGuardTests(_SolutionCase):
    SOLUTION_NAME = "S3-revert (no guard)"

    def _skip_fn(self):
        return s3_no_guard_skip_fn

    def test_s3_saves_healthy_match(self) -> None:
        self.assertTrue(self.criterion_saves_auto_matched())

    def test_s3_conflict_NOT_protected(self) -> None:
        """Documented limitation: S3 removes conflict protection."""
        _base_auto_save(healthy_item(), conflict_decision(), self._skip_fn())
        self.assertEqual(len(self.store.list_decisions()), 1)

    def test_s3_human_decision_preserved(self) -> None:
        self.criterion_human_decision_preserved()


if __name__ == "__main__":
    unittest.main(verbosity=2)
