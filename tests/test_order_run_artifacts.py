"""Tests for order run summary, AI trace, and manual review artifacts."""
from __future__ import annotations

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.core.artifact_run import artifact_run
from src.core.matching_models import MatchDecision, SearchMatch
from src.core.order_ai_matching import OrderAiOutcome
from src.core.utils.excel import Item
from src.tawreed.tawreed_match_logs import OrderItemSummary
from src.tawreed.tawreed_order_run_artifacts import (
    append_order_ai_trace_artifacts,
    append_order_item_artifacts,
)


class OrderRunArtifactsTests(unittest.TestCase):
    """Validate order-level trace and review artifact writers."""

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

    def test_manual_review_is_written_for_no_results(self) -> None:
        """No-results item summaries create manual-review artifacts."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_2030", root):
                append_order_item_artifacts(
                    "wardany", self._item(), self._summary("no-results"),
                    MatchDecision(None, [], "none"), None,
                )
            run_dir = root / "order/wardany/20260513_2030"
            rows = self._csv_rows(run_dir / "manual_review_20260513_2030.csv")
            self.assertEqual(rows[0]["status"], "no-results")
            self.assertEqual(rows[0]["manual_decision"], "")

    @staticmethod
    def _item() -> Item:
        return Item("1", "Panadol", 1)

    @staticmethod
    def _summary(status: str = "matched-only") -> OrderItemSummary:
        return OrderItemSummary(status=status, reason="done")

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
