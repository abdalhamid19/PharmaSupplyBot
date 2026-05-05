"""Tests for the per-worker summary merger."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from src.tawreed.order_result_merger import merge_worker_summaries


class MergeWorkerSummariesTests(unittest.TestCase):
    """Contract tests for merge_worker_summaries across typical scenarios."""

    def setUp(self) -> None:
        """Create a temporary working directory with an artifacts subdirectory."""
        self._tmp = tempfile.TemporaryDirectory()
        self._original_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.artifacts_dir = Path("artifacts") / "testprofile"
        self.artifacts_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        """Restore original working directory and cleanup."""
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def test_merges_two_worker_csv_files(self) -> None:
        """Two worker CSV files are concatenated into one canonical CSV."""
        self._write_csv("order_result_summary.worker_0.csv", ["a", "1"])
        self._write_csv("order_result_summary.worker_1.csv", ["b", "2"])
        merge_worker_summaries("testprofile", "order_result_summary")
        merged = self._read_csv("order_result_summary.csv")
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["col1"], "a")
        self.assertEqual(merged[1]["col1"], "b")

    def test_no_worker_files_leaves_no_output(self) -> None:
        """When no worker files exist the merger does nothing."""
        merge_worker_summaries("testprofile", "order_result_summary")
        self.assertFalse((self.artifacts_dir / "order_result_summary.csv").exists())

    def test_removes_worker_files_after_merge(self) -> None:
        """Worker partition files are cleaned up after a successful merge."""
        self._write_csv("order_result_summary.worker_0.csv", ["x", "9"])
        merge_worker_summaries("testprofile", "order_result_summary")
        remaining = list(self.artifacts_dir.glob("*.worker_*"))
        self.assertEqual(remaining, [])

    def test_merged_xlsx_is_created(self) -> None:
        """Merged XLSX file is produced alongside the CSV."""
        self._write_csv("order_result_summary.worker_0.csv", ["c", "3"])
        merge_worker_summaries("testprofile", "order_result_summary")
        self.assertTrue((self.artifacts_dir / "order_result_summary.xlsx").exists())

    def _write_csv(self, name: str, row_values: list[str]) -> None:
        """Write a minimal CSV worker file."""
        path = self.artifacts_dir / name
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["col1", "col2"])
            writer.writeheader()
            writer.writerow({"col1": row_values[0], "col2": row_values[1]})

    def _read_csv(self, name: str) -> list[dict]:
        """Read the canonical CSV file."""
        path = self.artifacts_dir / name
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


if __name__ == "__main__":
    unittest.main()
