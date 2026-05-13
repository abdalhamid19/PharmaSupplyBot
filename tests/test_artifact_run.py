"""Tests for run-scoped artifact path helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.core.artifact_run import (
    artifact_filename,
    artifact_run,
    current_artifact_run,
    minute_run_id,
    run_control_dir,
    unique_path,
    unique_run_id,
)


class ArtifactRunTests(unittest.TestCase):
    """Validate timestamped command artifact primitives."""

    def test_minute_run_id_uses_expected_format(self) -> None:
        """Return a sortable minute-level timestamp."""
        now = datetime(2026, 5, 13, 18, 30, 45)
        self.assertEqual(minute_run_id(now), "20260513_1830")

    def test_context_builds_command_profile_run_directory(self) -> None:
        """Create and expose the active command/profile/run directory."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_1830", root) as run:
                self.assertEqual(run.directory, root / "order/wardany/20260513_1830")
                self.assertTrue(run.directory.is_dir())
                self.assertEqual(current_artifact_run(), run)
            self.assertIsNone(current_artifact_run())

    def test_unique_helpers_suffix_collisions(self) -> None:
        """Add numeric suffixes when a run id or file path already exists."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            (root / "order/wardany/20260513_1830").mkdir(parents=True)
            path = root / "order/wardany/summary.csv"
            path.write_text("", encoding="utf-8")
            self.assertTrue(unique_run_id("order", "wardany", root).startswith("20"))
            self.assertEqual(unique_path(path).name, "summary_2.csv")

    def test_artifact_filename_uses_active_run_id(self) -> None:
        """Build timestamped file names from the active run."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "20260513_1830", root):
                name = artifact_filename("matching_trace", ".csv", "worker_1")
        self.assertEqual(name, "matching_trace_worker_1_20260513_1830.csv")

    def test_run_control_dir_is_command_scoped(self) -> None:
        """Place run-control files under command-specific directories."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            directory = run_control_dir("order", root)
            self.assertEqual(directory, root / "run-control/order")
            self.assertTrue(directory.is_dir())


if __name__ == "__main__":
    unittest.main()
