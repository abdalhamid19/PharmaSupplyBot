"""H5 regression guard (post-fix): store-served matches are not re-saved.

A 999.0 'Approved by saved manual review' decision must skip re-saving;
fresh matches (score != 999) must be saved.
"""

from __future__ import annotations

from src.core.matching_types import MatchDecision, SearchMatch
from tests.hypotheses.automatched._framework import (
    HypothesisCase, make_item, make_candidate,
)


class H5ForcedMatchGuardTests(HypothesisCase):
    PROBABILITY = 15
    NAME = "H5 forced-match guard (regression guard)"

    def test_h5_forced_match_guard_skips_re_save(self) -> None:
        decision = MatchDecision(
            best_match=SearchMatch(
                query="PANADOL EXTRA", row_index=0, score=999.0,
                data=make_candidate(),
            ),
            diagnostics=[],
            final_reason="Approved by saved manual review.",
        )
        self.run_production_flow(decision=decision)
        self.assertEqual(len(self.auto_rows()), 0)

    def test_h5_fresh_match_is_saved(self) -> None:
        self.run_production_flow()  # decision score=95.0
        self.assertEqual(len(self.auto_rows()), 1)
