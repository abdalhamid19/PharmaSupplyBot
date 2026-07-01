"""Tests for corrected manual-review search sources."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.core.manual_review.manual_review_corrections import (
    corrected_items_from_manual_review_csv,
    corrected_items_from_manual_review_rows,
    write_corrected_review_csv,
)
from src.ui.manual_review.streamlit_manual_review_cli import corrected_review_search_command


class ManualReviewCorrectionsTests(unittest.TestCase):
    """Validate corrected manual-review rows can drive match-only search."""

    def test_corrected_rows_prefer_correct_query(self) -> None:
        rows = [
            {
                "item_code": "1",
                "item_name": "Wrong",
                "item_qty": "2",
                "correct_query": "Correct Search",
                "correct_product_name": "Correct Product",
            },
            {"item_code": "2", "item_name": "Rejected", "not_matching": True},
        ]

        items = corrected_items_from_manual_review_rows(rows)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Correct Search")
        self.assertEqual(items[0].qty, 2)

    def test_write_and_read_corrected_review_csv(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "manual_review_corrections.csv"
            write_corrected_review_csv(
                [{"item_code": "1", "item_name": "A", "correct_product_name": "B"}],
                path,
            )
            items = corrected_items_from_manual_review_csv(path)

        self.assertEqual(items[0].name, "B")

    def test_corrected_review_search_command_is_match_only(self) -> None:
        command = corrected_review_search_command(
            Path("config.yaml"),
            Path("artifacts/order/wardany/20260514_2107"),
            Path("manual_review_corrections.csv"),
        )

        self.assertEqual(command[command.index("--profile") + 1], "wardany")
        self.assertIn("--from-manual-review-corrections", command)
        self.assertIn("--match-only", command)


if __name__ == "__main__":
    unittest.main()
