"""Tests for Streamlit manual-review learning helpers."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.manual_review_store import ManualReviewDecision, ManualReviewStore
from src.ui.streamlit_manual_review import (
    editable_manual_review_rows,
    manual_review_decisions_from_rows,
    save_manual_review_rows,
)
from src.ui.streamlit_manual_review_remove import (
    manual_review_remove_command,
    write_not_matching_review_csv,
)


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
        self.assertEqual(decisions[0].manual_decision, "approved_match")
        self.assertEqual(decisions[0].correct_store_product_id, "store-1")

    def test_builds_not_matching_decision(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [
                {
                    "item_code": "123",
                    "item_name": "Panadol",
                    "not_matching": True,
                    "correct_store_product_id": "store-1",
                }
            ],
            "20260514_1252",
        )

        self.assertEqual(decisions[0].manual_decision, "not_matching")

    def test_skips_empty_unapproved_row(self) -> None:
        decisions = manual_review_decisions_from_rows(
            [{"item_code": "123", "item_name": "Panadol", "approved_match": False}],
            "20260514_1252",
        )

        self.assertEqual(decisions, [])

    def test_save_decision_can_be_read_by_new_store_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            count = save_manual_review_rows(
                [
                    {
                        "item_code": "123",
                        "item_name": "Panadol",
                        "approved_match": True,
                        "correct_store_product_id": "store-1",
                        "correct_query": "Panadol 24",
                    }
                ],
                "20260514_1252",
                db_path,
            )

            decision = ManualReviewStore(db_path).lookup("123", "Panadol")

        self.assertEqual(count, 1)
        self.assertIsNotNone(decision)
        self.assertEqual(decision.correct_store_product_id, "store-1")
        self.assertEqual(decision.correct_query, "Panadol 24")

    def test_editable_rows_show_saved_decision_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManualReviewStore(Path(temp_dir) / "manual.sqlite3")
            store.upsert(
                ManualReviewDecision(
                    "123", "Panadol", True, "store-2", "Panadol Extra", "Pana"
                )
            )

            rows = editable_manual_review_rows(
                [{"item_code": "123", "item_name": "Panadol"}], store
            )

        self.assertEqual(rows[0]["decision_source"], "saved_manual_review")
        self.assertTrue(rows[0]["approved_match"])
        self.assertFalse(rows[0]["not_matching"])
        self.assertEqual(rows[0]["correct_store_product_id"], "store-2")

    def test_writes_not_matching_csv_for_current_run_removal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "artifacts/order/wardany/20260514_2107"
            run_dir.mkdir(parents=True)

            path = write_not_matching_review_csv(
                [
                    {"item_code": "1", "item_name": "Panadol", "not_matching": True},
                    {"item_code": "2", "item_name": "Cetal", "not_matching": False},
                ],
                run_dir,
            )
            content = path.read_text(encoding="utf-8")

        self.assertTrue(path.name.startswith("manual_review_not_matching_"))
        self.assertIn("Panadol", content)
        self.assertNotIn("Cetal", content)

    def test_manual_review_remove_command_uses_run_profile(self) -> None:
        command = manual_review_remove_command(
            Path("config.yaml"),
            Path("artifacts/order/wardany/20260514_2107"),
            Path("manual.csv"),
        )

        self.assertEqual(command[command.index("--profile") + 1], "wardany")
        self.assertIn("--from-manual-review", command)


if __name__ == "__main__":
    unittest.main()
