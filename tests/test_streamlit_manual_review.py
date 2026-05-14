"""Tests for Streamlit manual-review learning helpers."""

from __future__ import annotations

import unittest

from src.ui.streamlit_manual_review import manual_review_decisions_from_rows


class StreamlitManualReviewTests(unittest.TestCase):
    """Validate conversion from edited UI rows to persisted decisions."""

    def test_builds_decision_from_approved_checkbox(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [
                {
                    "item_code": "123",
                    "item_name": "Panadol",
                    "approved_match": True,
                    "correct_store_product_id": "store-1",
                }
            ],
            "20260514_1252",
        )

        self.assertEqual(len(decisions), 1)
        self.assertTrue(decisions[0].approved)
        self.assertEqual(decisions[0].correct_store_product_id, "store-1")

    def test_skips_empty_unapproved_row(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [{"item_code": "123", "item_name": "Panadol", "approved_match": False}],
            "20260514_1252",
        )

        self.assertEqual(decisions, [])


if __name__ == "__main__":
    unittest.main()
