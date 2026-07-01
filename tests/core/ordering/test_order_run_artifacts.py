"""Tests for order run summary, AI trace, and manual review artifacts."""
from __future__ import annotations

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.core.artifact_run import artifact_run
from src.core.matching_types import MatchDecision, SearchMatch
from src.core.ordering.order_ai_matching import OrderAiOutcome
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_match_logs import OrderResultSummary
from src.tawreed.order.tawreed_order_summary import (
    append_order_ai_trace_artifacts,
    append_order_item_artifacts,
)


from unittest.mock import patch

class OrderRunArtifactsTests(unittest.TestCase):
    """Validate order-level trace and review artifact writers."""

    def setUp(self) -> None:
        self.temp_db = TemporaryDirectory()
        db_path = Path(self.temp_db.name) / "test_manual.sqlite3"
        self.patcher1 = patch("src.core.manual_review.manual_review_runtime.DEFAULT_MANUAL_REVIEW_DB", db_path)
        self.patcher2 = patch("src.core.manual_review.manual_review_store.DEFAULT_MANUAL_REVIEW_DB", db_path)
        self.patcher1.start()
        self.patcher2.start()
        
    def tearDown(self) -> None:
        self.patcher1.stop()
        self.patcher2.stop()
        self.temp_db.cleanup()

    def test_writes_summary_trace_and_txt_files(self) -> None:
        """Write one item row plus detailed AI trace rows."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_2030", root):
                append_order_ai_trace_artifacts("wardany", self._item(), self._ai_outcome())
                append_order_item_artifacts(
                    "wardany", self._item(), self._summary(), self._decision(),
                    self._ai_outcome(),
                )
            run_dir = root / "order/wardany/20260513_2030"
            self.assertTrue((run_dir / "order_ai_trace_20260513_2030.csv").exists())
            self.assertTrue((run_dir / "order_ai_trace_20260513_2030.txt").exists())
            rows = self._csv_rows(run_dir / "order_item_summary_20260513_2030.csv")
            self.assertEqual(rows[0]["ai_status"], "ai_verified")
            self.assertEqual(rows[0]["ai_verified"], "True")
            self.assertEqual(rows[0]["matched"], "True")
            self.assertEqual(rows[0]["deterministic_match_found"], "True")
            self.assertEqual(rows[0]["manual_review_blocked_match"], "False")
            self.assertEqual(rows[0]["winner_store_product_id"], "s1")
            self.assertEqual(rows[0]["tie_break_reason"], "accepted")

    def test_ai_trace_writes_api_attempt_columns(self) -> None:
        """AI trace artifacts include provider attempt metadata."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_2030", root):
                append_order_ai_trace_artifacts(
                    "wardany", self._item(), self._ai_outcome_with_attempts()
                )
            rows = self._csv_rows(
                root
                / "order"
                / "wardany"
                / "20260513_2030"
                / "order_ai_trace_20260513_2030.csv"
            )

        attempt = next(row for row in rows if row["phase"] == "api_attempt_verify")
        self.assertEqual(attempt["provider"], "groq")
        self.assertEqual(attempt["model"], "openai/gpt-oss-120b")
        self.assertEqual(attempt["status"], "429")

    def test_manual_review_is_written_for_reviewable_statuses(self) -> None:
        """Reviewable item summaries create manual-review artifacts."""
        reviewable_statuses = ("no-results", "not-orderable", "manual-review-required")
        for status in reviewable_statuses:
            with self.subTest(status=status):
                self._assert_manual_review_status(status)

    @patch("src.core.manual_review.manual_review_runtime.saved_manual_review_decision")
    def _assert_manual_review_status(self, status: str, mock_saved_decision) -> None:
        """Write one summary and assert it is routed to manual review."""
        mock_saved_decision.return_value = None
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_2030", root):
                append_order_item_artifacts(
                    "wardany", self._item(), self._summary(status),
                    MatchDecision(None, [], "none"), None,
                )
            run_dir = root / "order/wardany/20260513_2030"
            rows = self._csv_rows(run_dir / "manual_review_20260513_2030.csv")
            self.assertEqual(rows[0]["status"], status)
            self.assertEqual(rows[0]["manual_review_reason_code"], status)
            self.assertTrue(rows[0]["manual_review_category"])
            self.assertEqual(rows[0]["matched"], "False")
            self.assertEqual(rows[0]["deterministic_match_found"], "False")
            self.assertEqual(rows[0]["manual_decision"], "")

    @patch("src.core.manual_review.manual_review_runtime.saved_manual_review_decision")
    def test_ai_blocked_match_is_not_final_actionable(self, mock_saved_decision) -> None:
        """A deterministic match blocked by AI is visible but not actionable."""
        mock_saved_decision.return_value = None
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            outcome = OrderAiOutcome(
                self._decision(), "ai_rejected", "local safety mismatch", 0.5, True,
                verify_result={"reason": "local_safety: component mismatch", "confidence": 0},
            )
            with artifact_run("order", "wardany", "20260513_2030", root):
                append_order_item_artifacts(
                    "wardany", self._item(), self._summary(), self._decision(), outcome,
                )
            rows = self._csv_rows(
                root / "order/wardany/20260513_2030/order_item_summary_20260513_2030.csv"
            )

        self.assertEqual(rows[0]["matched"], "False")
        self.assertEqual(rows[0]["deterministic_match_found"], "True")
        self.assertEqual(rows[0]["manual_review_blocked_match"], "True")
        self.assertEqual(rows[0]["manual_review_category"], "ai_rejected")
        self.assertEqual(rows[0]["candidate_safety_reason"], "component mismatch")

    @patch("src.core.manual_review.manual_review_runtime.saved_manual_review_decision")
    def test_auto_matched_failure_routes_to_review_when_flag_enabled(self, mock_saved):
        """A saved auto-match whose product is gone is sent back to review."""
        from types import SimpleNamespace

        from src.core.manual_review.manual_review_store import ManualReviewDecision
        from src.core.ordering.order_run_artifact_rows import manual_review_required

        mock_saved.return_value = ManualReviewDecision(
            "47853", "ZOCOZET", True, "2804012", manual_decision="auto_matched"
        )
        item = Item("47853", "ZOCOZET", 1)
        enabled = SimpleNamespace(enable_auto_match_re_review_on_fail=True)
        disabled = SimpleNamespace(enable_auto_match_re_review_on_fail=False)

        self.assertTrue(manual_review_required(item, "not-orderable", None, enabled))
        self.assertFalse(manual_review_required(item, "not-orderable", None, disabled))

    def test_preserve_existing_decision_blocks_overwrite_of_human_decision(self):
        """Auto-save must never overwrite a human approved/not-matching decision."""
        from src.core.manual_review.manual_review_store import ManualReviewDecision
        from src.tawreed.order.tawreed_order_summary import _preserve_existing_decision

        approved = ManualReviewDecision("1", "P", True, "s1", manual_decision="approved_match")
        not_matching = ManualReviewDecision("1", "P", False, "s1", manual_decision="not_matching")
        auto = ManualReviewDecision("1", "P", True, "s1", manual_decision="auto_matched")

        self.assertTrue(_preserve_existing_decision(approved))
        self.assertTrue(_preserve_existing_decision(not_matching))
        self.assertFalse(_preserve_existing_decision(auto))
        self.assertFalse(_preserve_existing_decision(None))

    def test_manufacturer_diagnostic_fields_in_summary_row(self):
        """Manufacturer diagnostic fields are added to artifact rows."""
        from src.core.ordering.order_run_artifact_rows import order_item_summary_row

        candidate = {
            "productNameEn": "Panadol",
            "productName": "بنادول",
            "storeProductId": "s1",
            "companyName": "GSK",
        }
        match = SearchMatch("Panadol GSK", 0, 95.0, candidate)
        decision = MatchDecision(match, [], "accepted")

        row = order_item_summary_row(
            self._item(), self._summary(), decision, None, None
        )

        self.assertEqual(row["query_manufacturer"], "GSK")
        self.assertEqual(row["candidate_manufacturer"], "GSK")
        self.assertEqual(row["manufacturer_check_decision"], "match")

    def test_manufacturer_conflict_detected_in_diagnostic_fields(self):
        """Manufacturer conflict is reflected in diagnostic fields."""
        from src.core.ordering.order_run_artifact_rows import order_item_summary_row
        from types import SimpleNamespace

        candidate = {
            "productNameEn": "Advil",
            "productName": "أدفيل",
            "storeProductId": "s2",
            "companyName": "Pfizer",
        }
        match = SearchMatch("Panadol GSK", 0, 95.0, candidate)
        decision = MatchDecision(match, [], "accepted")
        config = SimpleNamespace(manufacturer_match_threshold=0.85)

        row = order_item_summary_row(
            self._item(), self._summary(), decision, None, config
        )

        self.assertEqual(row["query_manufacturer"], "GSK")
        self.assertEqual(row["candidate_manufacturer"], "PFIZER")
        self.assertEqual(row["manufacturer_check_decision"], "conflict")

    @staticmethod
    def _item() -> Item:
        return Item("1", "Panadol", 1)

    @staticmethod
    def _summary(status: str = "matched-only") -> OrderResultSummary:
        return OrderResultSummary(status=status, reason="done")

    def _decision(self) -> MatchDecision:
        match = SearchMatch("Panadol", 0, 95.0, self._candidate())
        return MatchDecision(match, [], "accepted")

    def _ai_outcome(self) -> OrderAiOutcome:
        return OrderAiOutcome(
            self._decision(), "ai_verified", "ok", 0.96,
            verify_result={"reason": "ok", "confidence": 0.96, "model_used": "m1"},
        )

    def _ai_outcome_with_attempts(self) -> OrderAiOutcome:
        return OrderAiOutcome(
            self._decision(),
            "ai_verified",
            "ok",
            0.96,
            verify_result={
                "reason": "ok",
                "confidence": 0.96,
                "model_used": "m1",
                "_api_attempts": [
                    {
                        "attempt": 1,
                        "provider": "groq",
                        "model": "openai/gpt-oss-120b",
                        "status": 429,
                        "decision": "rate_limited",
                    }
                ],
            },
        )

    @staticmethod
    def _candidate() -> dict[str, object]:
        return {"productNameEn": "Panadol", "productName": "بنادول", "storeProductId": "s1"}

    @staticmethod
    def _csv_rows(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))


if __name__ == "__main__":
    unittest.main()
