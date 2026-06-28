import unittest

from src.core.matching_confidence import match_confidence
from src.core.matching_types import MatchDecision, SearchMatch
from src.core.utils.excel import Item


class MatchingConfidenceTests(unittest.TestCase):
    """Tests for the match_confidence function."""

    def test_no_match_returns_zero(self) -> None:
        """Check that no match results in a confidence score of 0.0."""
        item = Item(code="123", name="PANADOL 500MG TABS", qty=1)
        decision = MatchDecision(
            best_match=None, diagnostics=[], final_reason="No match"
        )
        score = match_confidence(decision, item, "PANADOL")
        self.assertEqual(score, 0.0)

    def test_exact_match_high_confidence(self) -> None:
        """Check that an exact match has high confidence."""
        item = Item(code="123", name="PANADOL 500MG TABS", qty=1)
        match = SearchMatch(
            query="PANADOL",
            row_index=0,
            score=20.0,
            data={
                "productNameEn": "PANADOL 500MG TABS",
                "availableQuantity": 100,
            },
        )
        decision = MatchDecision(
            best_match=match, diagnostics=[], final_reason="Accepted"
        )
        score = match_confidence(decision, item, "PANADOL")
        self.assertGreaterEqual(score, 0.95)

    def test_different_brand_low_confidence(self) -> None:
        """Check that a brand mismatch reduces confidence."""
        item = Item(code="123", name="PANADOL 500MG TABS", qty=1)
        match = SearchMatch(
            query="PANADOL",
            row_index=0,
            score=10.0,
            data={
                "productNameEn": "BRUFEN 500MG TABS",
                "availableQuantity": 100,
            },
        )
        decision = MatchDecision(
            best_match=match, diagnostics=[], final_reason="Accepted"
        )
        score = match_confidence(decision, item, "PANADOL")
        self.assertLess(score, 0.80)
