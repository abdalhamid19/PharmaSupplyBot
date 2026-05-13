"""Tests for merging order worker trace and review artifacts."""

from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from src.tawreed.order_worker_artifact_merger import merge_order_worker_artifacts


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
        self._write_csv("order_ai_trace_worker_0.csv", "verify")
        self._write_csv("order_ai_trace_worker_1.csv", "review")
        (self.artifacts_dir / "order_ai_trace_worker_0.txt").write_text(
            "worker0\n", encoding="utf-8"
        )
        (self.artifacts_dir / "order_ai_trace_worker_1.txt").write_text(
            "worker1\n", encoding="utf-8"
        )

        merge_order_worker_artifacts("wardany", ("order_ai_trace",))

        rows = self._read_csv("order_ai_trace.csv")
        self.assertEqual([row["phase"] for row in rows], ["verify", "review"])
        self.assertEqual(
            (self.artifacts_dir / "order_ai_trace.txt").read_text(encoding="utf-8"),
            "worker0\nworker1\n",
        )
        self.assertFalse(list(self.artifacts_dir.glob("order_ai_trace_worker_*.*")))

    def _write_csv(self, name: str, phase: str) -> None:
        path = self.artifacts_dir / name
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["phase"])
            writer.writeheader()
            writer.writerow({"phase": phase})

    def _read_csv(self, name: str) -> list[dict[str, str]]:
        path = self.artifacts_dir / name
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


if __name__ == "__main__":
    unittest.main()
