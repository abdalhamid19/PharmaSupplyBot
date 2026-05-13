"""Tests for legacy artifact migration."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.migrate_artifacts import migrate_artifacts


class MigrateArtifactsTests(unittest.TestCase):
    """Validate safe movement from flat artifact directories."""

    def test_moves_profile_outputs_and_preserves_catalog(self) -> None:
        """Move flat profile files to legacy and copy latest catalog."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            profile = root / "wardany"
            profile.mkdir(parents=True)
            (profile / "order_result_summary.csv").write_text("x", encoding="utf-8")
            (profile / "tawreed_products.csv").write_text("sku", encoding="utf-8")
            migrate_artifacts(root, "20260513_1830")
            legacy = root / "legacy/wardany/20260513_1830"
            catalog = root / "export-products/wardany/20260513_1830"
            self.assertTrue((legacy / "order_result_summary.csv").exists())
            self.assertTrue((catalog / "tawreed_products_20260513_1830.csv").exists())
            self.assertFalse(profile.exists())

    def test_moves_matching_and_run_control_to_legacy(self) -> None:
        """Move old shared matching and run_control directories."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            (root / "matching").mkdir(parents=True)
            (root / "run_control").mkdir()
            migrate_artifacts(root, "20260513_1830")
            self.assertTrue((root / "legacy/matching/20260513_1830").is_dir())
            self.assertTrue((root / "legacy/run_control/20260513_1830").is_dir())

    def test_keeps_command_directories_in_place(self) -> None:
        """Avoid moving the new command-scoped artifact directories."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            command_dir = root / "order/wardany/20260513_1830"
            command_dir.mkdir(parents=True)
            migrate_artifacts(root, "20260513_1831")
            self.assertTrue(command_dir.exists())


if __name__ == "__main__":
    unittest.main()
