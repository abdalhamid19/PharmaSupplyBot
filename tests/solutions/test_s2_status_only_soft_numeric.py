"""S2 scoring: status-only soft-numeric floor without rewriting rejection reason.

Useful belt-and-suspenders layer, but alone leaves artifact reasons noisy.
"""

from __future__ import annotations

import unittest

from src.core.matching_types import CandidateMatchDiagnostic, MatchScoreBreakdown
from src.tawreed.tawreed_summary import _diagnostic_missing_orderable_identity


def _diag(score: float, reason: str, store_id: str = "") -> CandidateMatchDiagnostic:
    candidate = {"productNameEn": "X", "storeProductId": store_id}
    breakdown = MatchScoreBreakdown(
        sequence_score=0.0,
        overlap_score=0.0,
        numeric_overlap=0.0,
        exact_bonus=0.0,
        availability_bonus=0.0,
        critical_penalty=0.0,
        extra_token_penalty=0.0,
        semantic_penalty=0.0,
        total_score=score,
    )
    return CandidateMatchDiagnostic(
        query="q",
        row_index=0,
        score=score,
        sort_key=(score, 0, 0.0, 0, 0, 0),
        accepted=False,
        accepted_reason="",
        rejection_reason=reason,
        breakdown=breakdown,
        candidate=candidate,
    )


class Solution2StatusOnlyTests(unittest.TestCase):
    """Score solution S2 status classifier extension."""

    SOLUTION_SCORE = 0.78

    def test_soft_numeric_high_score_is_not_orderable(self) -> None:
        diag = _diag(10.0, "unrequested numeric token: 50")
        self.assertTrue(_diagnostic_missing_orderable_identity(diag))

    def test_soft_numeric_low_score_is_not(self) -> None:
        diag = _diag(6.4, "unrequested numeric token: 5")
        self.assertFalse(_diagnostic_missing_orderable_identity(diag))

    def test_hard_identity_still_blocked(self) -> None:
        diag = _diag(15.0, "English name missing requested identity token")
        self.assertFalse(_diagnostic_missing_orderable_identity(diag))


if __name__ == "__main__":
    unittest.main()
