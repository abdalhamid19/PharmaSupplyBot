"""Tests for structured matching trace rows."""
from __future__ import annotations

import unittest

from src.core.matching_types import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
    SearchMatch,
)
from src.core.matching_trace import MAX_TRACE_CANDIDATE_ROWS, decision_trace_rows
from src.core.utils.excel import Item


class MatchingTraceTests(unittest.TestCase):
    """Validate trace fields used for run auditing."""

    def test_candidate_rows_include_reason_codes_and_score_breakdown(self) -> None:
        candidate = {"productNameEn": "Panadol", "storeProductId": "s1"}
        diagnostic = CandidateMatchDiagnostic(
            "Panadol",
            0,
            20.0,
            (20.0, 1, 1.0, 1, 5, 5),
            True,
            "exact_normalized_name_match",
            "",
            MatchScoreBreakdown(10, 3, 2, 1, 4, 0, 0, 0, 20),
            candidate,
        )
        decision = MatchDecision(
            SearchMatch("Panadol", 0, 20.0, candidate),
            [diagnostic],
            "Accepted: exact_normalized_name_match",
        )

        rows = decision_trace_rows(Item("1", "Panadol", 1), decision)

        self.assertEqual(rows[0]["final_reason_code"], "accepted")
        self.assertEqual(rows[0]["reason_code"], "exact_normalized_name_match")
        self.assertTrue(rows[0]["candidate_has_orderable_id"])
        self.assertEqual(rows[0]["score_sequence"], 10)
        self.assertEqual(rows[0]["score_availability_bonus"], 4)

    def test_empty_trace_row_has_final_reason_code(self) -> None:
        decision = MatchDecision(None, [], "No search candidates were returned.")

        rows = decision_trace_rows(Item("1", "Panadol", 1), decision)

        self.assertEqual(rows[0]["final_reason_code"], "no_search_candidates_were_returned")

    def test_candidate_trace_rows_are_bounded(self) -> None:
        candidate = {"productNameEn": "Panadol", "storeProductId": "s1"}
        diagnostics = [
            CandidateMatchDiagnostic(
                "Panadol", index, float(index), (float(index), 0, 0, 0, 0, index),
                False, "", "rejected", MatchScoreBreakdown(0, 0, 0, 0, 0, 0, 0, 0, 0),
                candidate,
            )
            for index in range(MAX_TRACE_CANDIDATE_ROWS + 5)
        ]

        rows = decision_trace_rows(Item("1", "Panadol", 1), MatchDecision(None, diagnostics, "x"))

        self.assertEqual(len(rows), MAX_TRACE_CANDIDATE_ROWS)


if __name__ == "__main__":
    unittest.main()
