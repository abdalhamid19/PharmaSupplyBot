"""Tests for UI selection to manual review decision conversion."""

import unittest

from src.core.manual_review_candidates import ReviewCandidateOption
from src.core.manual_review_selection import decision_from_selection
from src.core.utils.excel import Item


class ManualReviewSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = Item(code="ITM1", name="Test Item", qty="1")
        self.run_id = "run_123"

    def test_not_matching_takes_precedence(self) -> None:
        decision = decision_from_selection(
            self.item, None, not_matching=True, free_text_query="ignore", run_id=self.run_id
        )
        
        self.assertFalse(decision.approved)
        self.assertEqual(decision.manual_decision, "not_matching")
        self.assertEqual(decision.run_id, self.run_id)

    def test_free_text_query_creates_needs_correction(self) -> None:
        decision = decision_from_selection(
            self.item, None, not_matching=False, free_text_query="New Query", run_id=self.run_id
        )
        
        self.assertFalse(decision.approved)
        self.assertEqual(decision.manual_decision, "needs_correction")
        self.assertEqual(decision.correct_query, "New Query")

    def test_selected_option_creates_approved_match(self) -> None:
        option = ReviewCandidateOption(
            store_product_id="s123", name_en="EN Name", name_ar="AR Name",
            supplier="Supp", available_quantity=10, price=10.0, score=0.0,
            rejection_reason="", orderable=True,
        )
        
        decision = decision_from_selection(
            self.item, option, not_matching=False, free_text_query="", run_id=self.run_id
        )
        
        self.assertTrue(decision.approved)
        self.assertEqual(decision.manual_decision, "approved_match")
        self.assertEqual(decision.correct_store_product_id, "s123")
        self.assertEqual(decision.correct_product_name, "EN Name")

    def test_unorderable_selected_option_creates_approved_match(self) -> None:
        option = ReviewCandidateOption(
            store_product_id="", name_en="EN Name", name_ar="AR Name",
            supplier="Supp", available_quantity=10, price=10.0, score=0.0,
            rejection_reason="", orderable=False,
        )
        
        decision = decision_from_selection(
            self.item, option, not_matching=False, free_text_query="", run_id=self.run_id
        )
        
        self.assertTrue(decision.approved)
        self.assertEqual(decision.manual_decision, "approved_match")
        self.assertEqual(decision.correct_store_product_id, "")
        self.assertEqual(decision.correct_product_name, "EN Name")
        self.assertEqual(decision.correct_product_name_ar, "AR Name")

    def test_no_action_returns_none(self) -> None:
        """Test that no explicit choice returns None (leave unmatched)."""
        decision = decision_from_selection(
            self.item, None, not_matching=False, free_text_query="", run_id=self.run_id
        )
        
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
