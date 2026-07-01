import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.views import streamlit_results


class StreamlitResultsTests(unittest.TestCase):
    def test_clear_profile_result_data_removes_profile_artifacts_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            profile_dir = artifacts_dir / "wardany"
            profile_dir.mkdir(parents=True)
            (profile_dir / "order_result_summary.csv").write_text("old\n", encoding="utf-8")
            nested_dir = profile_dir / "nested"
            nested_dir.mkdir()
            (nested_dir / "debug.txt").write_text("old\n", encoding="utf-8")
            other_profile_dir = artifacts_dir / "other"
            other_profile_dir.mkdir()
            (other_profile_dir / "keep.csv").write_text("keep\n", encoding="utf-8")

            with patch("src.ui.views.streamlit_results.ARTIFACTS_DIR", artifacts_dir):
                removed_count = streamlit_results.clear_profile_result_data("wardany")

            self.assertEqual(removed_count, 2)
            self.assertEqual(list(profile_dir.iterdir()), [])
            self.assertTrue((other_profile_dir / "keep.csv").exists())

    def test_safe_profile_artifact_paths_rejects_path_outside_artifacts_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            outside_dir = Path(temp_dir) / "outside"
            artifacts_dir.mkdir()
            outside_dir.mkdir()

            with patch("src.ui.views.streamlit_results.ARTIFACTS_DIR", artifacts_dir):
                with self.assertRaisesRegex(ValueError, "Refusing"):
                    streamlit_results.safe_profile_artifact_paths(outside_dir)

    def test_run_summary_rows_prefers_order_item_summary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "run"
            run_dir.mkdir()
            (run_dir / "match_only_summary_20260513_2030.csv").write_text(
                "kind\nold\n", encoding="utf-8"
            )
            (run_dir / "order_item_summary_20260513_2030.csv").write_text(
                "kind\nnew\n", encoding="utf-8"
            )

            rows = streamlit_results.run_summary_rows(run_dir)

        self.assertEqual(rows[0]["kind"], "new")


if __name__ == "__main__":
    unittest.main()
