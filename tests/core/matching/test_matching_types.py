"""Contract tests for shared matching result types."""

from __future__ import annotations

import unittest

from src.core.matching_types import DecisionSource, MatchDecision


class MatchingTypesContractTests(unittest.TestCase):
    """Verify construction compatibility for matching result types."""

    def test_legacy_match_decision_construction_defaults_to_scoring(self) -> None:
        decision = MatchDecision(None, [], "No match")

        self.assertEqual(decision.source, DecisionSource.SCORING)

    def test_match_decision_accepts_source_as_final_positional_field(self) -> None:
        decision = MatchDecision(
            None,
            [],
            "Saved manual review",
            DecisionSource.MANUAL_REVIEW_SAVED,
        )

        self.assertEqual(decision.source, DecisionSource.MANUAL_REVIEW_SAVED)

    def test_decision_source_values_remain_string_compatible(self) -> None:
        self.assertEqual(DecisionSource.SCORING.value, "scoring")
        self.assertIsInstance(DecisionSource.MANUAL_REVIEW_FORCED, str)


if __name__ == "__main__":
    unittest.main()
