"""Tests for the quality_metrics module."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.quality.quality_metrics import (
    RunQualityMetrics,
    compute_quality_metrics,
    compute_quality_metrics_from_directory,
    save_quality_report,
)

HEADERS = [
    "item_code", "item_name", "item_qty", "status", "reason", "matched_query",
    "deterministic_score", "matched", "deterministic_match_found",
    "manual_review_blocked_match", "matched_product_name_en",
    "matched_product_name_ar", "ai_status", "manual_review_required",
    "manual_review_category",
]


def _write_summary_csv(directory: Path, rows: list[dict]) -> Path:
    csv_path = directory / "order_item_summary_test.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            full_row = {header: "" for header in HEADERS}
            full_row.update(row)
            writer.writerow(full_row)
    return csv_path


class QualityMetricsTests(unittest.TestCase):
    def test_auto_match_rate_computation(self) -> None:
        rows = [
            {"status": "matched", "matched": "True", "manual_review_required": "False",
             "deterministic_match_found": "True", "ai_status": "ai_verified"},
            {"status": "matched", "matched": "True", "manual_review_required": "False",
             "deterministic_match_found": "True", "ai_status": "ai_verified"},
            {"status": "no-results", "matched": "False", "manual_review_required": "True",
             "deterministic_match_found": "False", "ai_status": "ai_rejected",
             "manual_review_category": "no_results"},
            {"status": "manual-review-required", "matched": "False",
             "manual_review_required": "True", "deterministic_match_found": "True",
             "ai_status": "ai_low_confidence",
             "manual_review_category": "low_confidence"},
        ]
        with TemporaryDirectory() as temporary:
            csv_path = _write_summary_csv(Path(temporary), rows)
            metrics = compute_quality_metrics(csv_path)

        self.assertEqual(metrics.total_items, 4)
        self.assertEqual(metrics.auto_matched, 2)
        self.assertEqual(metrics.auto_match_rate, 50.0)
        self.assertEqual(metrics.manual_review_required, 2)
        self.assertEqual(metrics.manual_review_rate, 50.0)
        self.assertEqual(metrics.no_results, 1)
        self.assertEqual(metrics.ai_verified, 2)
        self.assertEqual(metrics.ai_rejected, 1)
        self.assertEqual(metrics.ai_low_confidence, 1)
        self.assertEqual(metrics.deterministic_matched, 3)

    def test_category_counts_populated(self) -> None:
        rows = [
            {"status": "manual-review-required", "matched": "False",
             "manual_review_required": "True", "deterministic_match_found": "False",
             "ai_status": "ai_rejected", "manual_review_category": "brand_mismatch"},
            {"status": "manual-review-required", "matched": "False",
             "manual_review_required": "True", "deterministic_match_found": "False",
             "ai_status": "ai_rejected", "manual_review_category": "brand_mismatch"},
            {"status": "manual-review-required", "matched": "False",
             "manual_review_required": "True", "deterministic_match_found": "False",
             "ai_status": "ai_low_confidence", "manual_review_category": "low_confidence"},
        ]
        with TemporaryDirectory() as temporary:
            csv_path = _write_summary_csv(Path(temporary), rows)
            metrics = compute_quality_metrics(csv_path)

        self.assertEqual(metrics.category_counts["brand_mismatch"], 2)
        self.assertEqual(metrics.category_counts["low_confidence"], 1)

    def test_compute_from_directory(self) -> None:
        rows = [
            {"status": "matched", "matched": "True", "manual_review_required": "False",
             "deterministic_match_found": "True", "ai_status": "ai_verified"},
        ]
        with TemporaryDirectory() as temporary:
            _write_summary_csv(Path(temporary), rows)
            metrics = compute_quality_metrics_from_directory(Path(temporary))

        self.assertEqual(metrics.total_items, 1)
        self.assertEqual(metrics.auto_matched, 1)

    def test_save_quality_report_writes_file(self) -> None:
        rows = [
            {"status": "matched", "matched": "True", "manual_review_required": "False",
             "deterministic_match_found": "True", "ai_status": "ai_verified"},
            {"status": "no-results", "matched": "False", "manual_review_required": "True",
             "deterministic_match_found": "False", "ai_status": "ai_rejected",
             "manual_review_category": "no_results"},
        ]
        with TemporaryDirectory() as temporary:
            _write_summary_csv(Path(temporary), rows)
            report_path = save_quality_report(Path(temporary))

            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("Total items:", content)
            self.assertIn("Auto-matched:", content)
            self.assertIn("50.0%", content)

    def test_format_report_contains_sections(self) -> None:
        metrics = RunQualityMetrics(
            total_items=10,
            auto_matched=6,
            manual_review_required=3,
            no_results=1,
            status_counts={"matched": 6, "no-results": 1, "manual-review-required": 3},
            category_counts={"brand_mismatch": 2, "low_confidence": 1},
        )
        report = metrics.format_report()

        self.assertIn("ORDER MATCHING QUALITY REPORT", report)
        self.assertIn("Auto-matched:", report)
        self.assertIn("60.0%", report)
        self.assertIn("brand_mismatch", report)
        self.assertIn("Status Distribution", report)
        self.assertIn("Manual Review Categories", report)

    def test_empty_csv_returns_zero_metrics(self) -> None:
        with TemporaryDirectory() as temporary:
            csv_path = _write_summary_csv(Path(temporary), [])
            metrics = compute_quality_metrics(csv_path)

        self.assertEqual(metrics.total_items, 0)
        self.assertEqual(metrics.auto_match_rate, 0.0)
        self.assertEqual(metrics.manual_review_rate, 0.0)

    def test_missing_csv_raises_file_not_found(self) -> None:
        with TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                compute_quality_metrics_from_directory(Path(temporary))


if __name__ == "__main__":
    unittest.main()
