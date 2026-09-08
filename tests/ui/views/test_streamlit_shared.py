import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui import streamlit_shared
from src.ui.streamlit_shared import (
    DEFAULT_CONFIG_PATH,
    FALLBACK_CONFIG_PATH,
    load_csv_rows,
    load_new_summary_rows,
    load_xlsx_rows,
    resolved_streamlit_config_path,
)


class StreamlitSharedTests(unittest.TestCase):
    def setUp(self) -> None:
        streamlit_shared._read_table_rows_cached.clear()

    def tearDown(self) -> None:
        streamlit_shared._read_table_rows_cached.clear()

    def test_resolved_streamlit_config_path_uses_existing_selected_path(self) -> None:
        with patch.object(Path, "exists", autospec=True) as exists:
            exists.side_effect = lambda path: path == DEFAULT_CONFIG_PATH
            self.assertEqual(
                resolved_streamlit_config_path(DEFAULT_CONFIG_PATH),
                DEFAULT_CONFIG_PATH,
            )

    def test_resolved_streamlit_config_path_falls_back_for_missing_default(self) -> None:
        with patch.object(Path, "exists", autospec=True) as exists:
            exists.side_effect = lambda path: path == FALLBACK_CONFIG_PATH
            self.assertEqual(
                resolved_streamlit_config_path(DEFAULT_CONFIG_PATH),
                FALLBACK_CONFIG_PATH,
            )

    def test_resolved_streamlit_config_path_keeps_custom_missing_path(self) -> None:
        custom_path = Path("missing-custom.yaml")
        with patch.object(Path, "exists", autospec=True, return_value=False):
            self.assertEqual(resolved_streamlit_config_path(custom_path), custom_path)

    def test_load_csv_rows_reuses_cache_for_unchanged_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "summary.csv"
            csv_path.write_text("name,quantity\nalpha,\nbeta,2\n", encoding="utf-8")

            with patch.object(
                streamlit_shared.pd,
                "read_csv",
                wraps=streamlit_shared.pd.read_csv,
            ) as reader:
                first_rows = load_csv_rows(csv_path)
                second_rows = load_csv_rows(csv_path)

            self.assertEqual(
                first_rows,
                [{"name": "alpha", "quantity": ""}, {"name": "beta", "quantity": 2}],
            )
            self.assertEqual(second_rows, first_rows)
            self.assertEqual(reader.call_count, 1)

    def test_load_csv_rows_invalidates_cache_when_file_changes(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "summary.csv"
            csv_path.write_text("name\nfirst\n", encoding="utf-8")
            first_rows = load_csv_rows(csv_path)
            original_mtime_ns = csv_path.stat().st_mtime_ns

            csv_path.write_text("name\nsecond\n", encoding="utf-8")
            current_atime_ns = csv_path.stat().st_atime_ns
            os.utime(
                csv_path,
                ns=(current_atime_ns, original_mtime_ns + 1_000_000),
            )

            changed_rows = load_csv_rows(csv_path)

            self.assertEqual(first_rows, [{"name": "first"}])
            self.assertEqual(changed_rows, [{"name": "second"}])

    def test_load_csv_rows_returns_empty_for_missing_or_empty_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.csv"
            empty_path = Path(temporary_directory) / "empty.csv"
            empty_path.write_text("name,quantity\n", encoding="utf-8")

            with patch.object(
                streamlit_shared.pd,
                "read_csv",
                wraps=streamlit_shared.pd.read_csv,
            ) as reader:
                self.assertEqual(load_csv_rows(missing_path), [])
                self.assertEqual(load_csv_rows(empty_path), [])

            self.assertEqual(reader.call_count, 1)

    def test_load_xlsx_rows_uses_cached_reader(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            xlsx_path = Path(temporary_directory) / "summary.xlsx"
            xlsx_path.write_bytes(b"placeholder")

            with patch.object(
                streamlit_shared.pd,
                "read_excel",
                return_value=streamlit_shared.pd.DataFrame({"name": ["alpha"]}),
            ) as reader:
                first_rows = load_xlsx_rows(xlsx_path)
                second_rows = load_xlsx_rows(xlsx_path)

            self.assertEqual(first_rows, [{"name": "alpha"}])
            self.assertEqual(second_rows, first_rows)
            self.assertEqual(reader.call_count, 1)

    def test_load_new_summary_rows_returns_only_appended_records(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "summary.csv"
            csv_path.write_text(
                "name,quantity\nalpha,1\nbeta,2\n", encoding="utf-8"
            )

            appended_rows = load_new_summary_rows(csv_path, previous_row_count=1)

        self.assertEqual(appended_rows, [{"name": "beta", "quantity": 2}])

    def test_load_new_summary_rows_handles_multiline_csv_fields(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "summary.csv"
            csv_path.write_text(
                'name,reason\n"alpha\npack",first\n"beta\npack",second\n',
                encoding="utf-8",
            )

            appended_rows = load_new_summary_rows(csv_path, previous_row_count=1)

        self.assertEqual(appended_rows, [{"name": "beta\npack", "reason": "second"}])


if __name__ == "__main__":
    unittest.main()
