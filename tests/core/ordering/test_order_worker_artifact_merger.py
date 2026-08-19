"""Tests for merging order worker trace and review artifacts."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from src.tawreed.artifacts.order_worker_artifact_merger import merge_order_worker_artifacts


class MergeOrderWorkerArtifactsTests(unittest.TestCase):
    """Verify CSV/TXT worker partitions become canonical order artifacts."""

    def setUp(self) -> None:
        """Create an isolated artifact tree."""
        self._tmp = tempfile.TemporaryDirectory()
        self._original_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        self.artifacts_dir = Path("artifacts") / "wardany"
        self.artifacts_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        """Restore the process working directory."""
        os.chdir(self._original_cwd)
        self._tmp.cleanup()

    def test_merges_csv_and_text_worker_partitions(self) -> None:
        """Worker CSV and TXT files are merged then removed."""
        self._write_csv("order_matching_trace_worker_0.csv", "local_match")
        self._write_csv("order_matching_trace_worker_1.csv", "manual_review")
        (self.artifacts_dir / "order_matching_trace_worker_0.txt").write_text(
            "worker0\n", encoding="utf-8"
        )
        (self.artifacts_dir / "order_matching_trace_worker_1.txt").write_text(
            "worker1\n", encoding="utf-8"
        )

        merge_order_worker_artifacts("wardany", ("order_matching_trace",))

        rows = self._read_csv("order_matching_trace.csv")
        self.assertEqual([row["phase"] for row in rows], ["local_match", "manual_review"])
        self.assertEqual(
            (self.artifacts_dir / "order_matching_trace.txt").read_text(encoding="utf-8"),
            "worker0\nworker1\n",
        )
        self.assertFalse(list(self.artifacts_dir.glob("order_matching_trace_worker_*.*")))

    def test_merges_worker_partitions_with_union_schema(self) -> None:
        """Worker CSV files can contain different local matching columns."""
        self._write_rows(
            "order_matching_trace_worker_0.csv",
            [{"phase": "local_match", "score": "94"}],
        )
        self._write_rows(
            "order_matching_trace_worker_1.csv",
            [{"phase": "manual_review", "reason": "low_score"}],
        )

        merge_order_worker_artifacts("wardany", ("order_matching_trace",))

        rows = self._read_csv("order_matching_trace.csv")
        self.assertEqual(rows[0]["score"], "94")
        self.assertEqual(rows[0]["reason"], "")
        self.assertEqual(rows[1]["reason"], "low_score")

    def _write_csv(self, name: str, phase: str) -> None:
        self._write_rows(name, [{"phase": phase}])

    def _write_rows(self, name: str, rows: list[dict[str, str]]) -> None:
        path = self.artifacts_dir / name
        with path.open("w", encoding="utf-8", newline="") as f:
            fieldnames = list(rows[0])
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self.artifacts_dir / name
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


if __name__ == "__main__":
    unittest.main()
