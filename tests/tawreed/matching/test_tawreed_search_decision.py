"""Tests for shared Tawreed match-decision annotations."""

from __future__ import annotations

import unittest

from src.core.matching_types import MatchDecision
from src.tawreed.matching.tawreed_search_decision import mark_forced_manual_review


class TawreedSearchDecisionTests(unittest.TestCase):
    """Validate metadata added to approved manual-review decisions."""

    def test_marks_manual_review_source_without_changing_decision_fields(self) -> None:
        decision = MatchDecision(None, [], "Approved by saved manual review")

        marked_decision = mark_forced_manual_review(decision)

        self.assertEqual(marked_decision.best_match, decision.best_match)
        self.assertEqual(marked_decision.diagnostics, decision.diagnostics)
        self.assertEqual(marked_decision.final_reason, decision.final_reason)
        self.assertEqual(marked_decision.source.value, "manual_review_forced")
