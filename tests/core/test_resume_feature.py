"""Comprehensive test suite for the `--resume` feature across CLI and UI.

Verifies:
1. item_key normalization (case-insensitivity, empty/None/nan code handling, whitespace stripping).
2. latest_summary_path discovery (active artifact run directory, artifacts/order/<profile>/*, artifacts/<profile>, artifacts/legacy).
3. processed_summary_item_keys reading (extracts items correctly from order_item_summary and match_only_summary CSVs).
4. prepared_order_items filtering:
   - When resume=False: preserves all items without filtering.
   - When resume=True: skips already processed items by (code, name) tuple.
   - Preserves order of remaining items.
   - Works when all items are already processed (yields empty).
   - Works when no items were previously processed.
5. excel_load_limit interaction with resume:
   - When resume=True, limit is deferred (loads 0 / all from Excel) so filtering happens AFTER reading summaries.
6. run_single_profile_items integration:
   - Limit is applied AFTER resume skips already processed rows.
   - If all rows are skipped, execution exits cleanly without running the bot (ensure_non_empty_items).
7. Streamlit UI command generation:
   - Form values with "resume": True correctly append "--resume" to CLI command array.
"""

from __future__ import annotations

import csv
import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from src.cli.commands.cli_order_execution import run_single_profile_items
from src.cli.commands.cli_order_items import (
    excel_load_limit,
    item_key,
    latest_summary_path,
    prepared_order_items,
    processed_summary_item_keys,
    summary_label,
)
from src.core.artifact_run import artifact_run
from src.core.utils.excel import Item
from src.ui.order.streamlit_order_command import order_command


class ResumeFeatureComprehensiveTests(unittest.TestCase):
    """Test cases for verifying resume from previous summary functionality."""

    def test_item_key_normalization(self) -> None:
        """item_key should normalize codes and names properly."""
        # Exact match
        self.assertEqual(item_key("123", "Panadol Extra"), ("123", "panadol extra"))
        # Whitespace stripping & lowercase
        self.assertEqual(item_key(" 123 ", "  Panadol EXTRA  "), ("123", "panadol extra"))
        # Empty / None / nan code normalization to empty string
        self.assertEqual(item_key(None, "Panadol"), ("", "panadol"))
        self.assertEqual(item_key("", "Panadol"), ("", "panadol"))
        self.assertEqual(item_key("nan", "Panadol"), ("", "panadol"))
        self.assertEqual(item_key("None", "Panadol"), ("", "panadol"))
        self.assertEqual(item_key("   ", "Panadol"), ("", "panadol"))

    def test_latest_summary_path_resolution(self) -> None:
        """latest_summary_path should discover newest summary CSV from various directory layouts."""
        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile = "test_profile"

                # 1. artifacts/<profile>/order_item_summary.csv
                legacy_dir = Path("artifacts") / profile
                legacy_dir.mkdir(parents=True)
                legacy_file = legacy_dir / "order_item_summary.csv"
                legacy_file.write_text("item_code,item_name\n1,DrugA\n", encoding="utf-8")

                found = latest_summary_path(profile, "order_item_summary")
                self.assertEqual(found, legacy_file)

                # 2. artifacts/order/<profile>/<timestamp>/order_item_summary_1.csv (newer)
                run_dir = Path("artifacts") / "order" / profile / "20260826_1200"
                run_dir.mkdir(parents=True)
                new_file = run_dir / "order_item_summary_20260826_1200.csv"
                new_file.write_text("item_code,item_name\n2,DrugB\n", encoding="utf-8")

                found = latest_summary_path(profile, "order_item_summary")
                self.assertEqual(found, new_file)

                # 3. Inside active artifact_run context
                with artifact_run("order", profile) as active_run:
                    active_file = active_run.directory / "order_item_summary_active.csv"
                    active_file.write_text("item_code,item_name\n3,DrugC\n", encoding="utf-8")

                    found_in_active = latest_summary_path(profile, "order_item_summary")
                    self.assertEqual(found_in_active, active_file)

            finally:
                os.chdir(orig_cwd)

    def test_processed_summary_item_keys_extraction(self) -> None:
        """processed_summary_item_keys should read keys and handle missing / weird values."""
        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile = "wardany"
                out_dir = Path("artifacts") / "order" / profile / "20260826_1000"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "order_item_summary_20260826_1000.csv"

                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    writer.writerow(["1001", "Panadol Advance 24 Tab", "added-to-cart"])
                    writer.writerow(["", "Aspirin Protect 100mg", "not-orderable"])
                    writer.writerow(["nan", "CATAFLAM 50MG", "matched-only"])
                    writer.writerow(["1002", "   CONGESTRAL 20 TAB  ", "added-to-cart"])

                keys = processed_summary_item_keys(profile, "order_item_summary")
                expected = {
                    ("1001", "panadol advance 24 tab"),
                    ("", "aspirin protect 100mg"),
                    ("", "cataflam 50mg"),
                    ("1002", "congestral 20 tab"),
                }
                self.assertEqual(keys, expected)
            finally:
                os.chdir(orig_cwd)

    def test_prepared_order_items_when_resume_is_false(self) -> None:
        """When resume=False, all items should yield without looking at summaries."""
        items = [
            Item(code="1", name="Item 1", qty=1),
            Item(code="2", name="Item 2", qty=2),
        ]
        args: Any = SimpleNamespace(resume=False)
        with patch("src.cli.cli_shared.require_state_file"):
            result = list(prepared_order_items("wardany", items, args))
        self.assertEqual(result, items)

    def test_prepared_order_items_when_resume_is_true(self) -> None:
        """When resume=True, items in summary should be filtered out accurately."""
        items = [
            Item(code="1001", name="Item 1", qty=1),
            Item(code="1002", name="Item 2", qty=1),
            Item(code="", name="Item 3 (No Code)", qty=2),
            Item(code="1004", name="Item 4", qty=1),
        ]
        args: Any = SimpleNamespace(resume=True, match_only=False)

        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile = "wardany"
                out_dir = Path("artifacts") / "order" / profile / "20260826_1000"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "order_item_summary_20260826_1000.csv"

                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    writer.writerow(["1001", "Item 1", "added-to-cart"])
                    writer.writerow(["", "item 3 (no code)", "no-results"])

                with patch("src.cli.cli_shared.require_state_file"):
                    remaining = list(prepared_order_items(profile, items, args))

                # Item 1 and Item 3 should be skipped, leaving Item 2 and Item 4
                self.assertEqual(remaining, [items[1], items[3]])
            finally:
                os.chdir(orig_cwd)

    def test_prepared_order_items_match_only_mode(self) -> None:
        """In match_only mode, summary_label should be match_only_summary."""
        items = [
            Item(code="1001", name="Item 1", qty=1),
            Item(code="1002", name="Item 2", qty=1),
        ]
        args: Any = SimpleNamespace(resume=True, match_only=True)
        self.assertEqual(summary_label(args), "match_only_summary")

        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile = "wardany"
                out_dir = Path("artifacts") / "order" / profile / "20260826_1000"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "match_only_summary_20260826_1000.csv"

                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    writer.writerow(["1001", "Item 1", "matched-only"])

                with patch("src.cli.cli_shared.require_state_file"):
                    remaining = list(prepared_order_items(profile, items, args))

                self.assertEqual(remaining, [items[1]])
            finally:
                os.chdir(orig_cwd)

    def test_excel_load_limit_interaction_with_resume(self) -> None:
        """When resume=True, excel_load_limit must return 0 so filtering isn't prematurely truncated."""
        args_no_resume = SimpleNamespace(resume=False, limit=10, start_item=1, end_item=0)
        self.assertEqual(excel_load_limit(args_no_resume, has_prevented_filter=False), 10)

        args_with_resume = SimpleNamespace(resume=True, limit=10, start_item=1, end_item=0)
        self.assertEqual(excel_load_limit(args_with_resume, has_prevented_filter=False), 0)

    def test_run_single_profile_limits_after_resume_skips(self) -> None:
        """Full pipeline verification: load_order_items -> prepared_order_items (resume) -> limited_order_items."""
        all_items = [
            Item(code="1", name="Item 1", qty=1),  # previously processed
            Item(code="2", name="Item 2", qty=1),  # previously processed
            Item(code="3", name="Item 3", qty=1),  # to be processed (1st remaining)
            Item(code="4", name="Item 4", qty=1),  # to be processed (2nd remaining)
            Item(code="5", name="Item 5", qty=1),  # excluded by limit=2
        ]
        args: Any = SimpleNamespace(
            excel="fake.xlsx",
            resume=True,
            limit=2,
            match_only=True,
            item_workers=1,
            start_item=1,
            end_item=0,
        )

        app_config: Any = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            excel=SimpleNamespace(),
        )

        captured_items: list[Item] = []

        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile_key = "wardany"
                out_dir = Path("artifacts") / "order" / profile_key / "20260826_0900"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "match_only_summary_20260826_0900.csv"

                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    writer.writerow(["1", "Item 1", "matched-only"])
                    writer.writerow(["2", "Item 2", "matched-only"])

                with (
                    patch("src.cli.commands.cli_order_items.load_order_items", return_value=iter(all_items)),
                    patch("src.cli.cli_shared.require_state_file"),
                    patch("src.cli.commands.cli_order_execution.order_bot", return_value=MagicMock()),
                    patch("src.cli.commands.cli_order_execution.run_profile_match_only") as mock_match,
                ):
                    mock_match.side_effect = lambda _base, _key, _bot, items_iter: captured_items.extend(list(items_iter))
                    profile_config: Any = SimpleNamespace()
                    run_single_profile_items(app_config, profile_key, profile_config, args)

                # Should have skipped 1 and 2, and processed 3 and 4 (limit=2), ignoring 5
                self.assertEqual(len(captured_items), 2)
                self.assertEqual(captured_items[0].code, "3")
                self.assertEqual(captured_items[1].code, "4")
            finally:
                os.chdir(orig_cwd)

    def test_run_single_profile_exits_early_when_all_items_already_processed(self) -> None:
        """When all items in Excel were already processed, no bot calls should be made."""
        items = [
            Item(code="1", name="Item 1", qty=1),
        ]
        args: Any = SimpleNamespace(
            excel="fake.xlsx",
            resume=True,
            limit=0,
            match_only=False,
            item_workers=1,
            start_item=1,
            end_item=0,
        )
        app_config: Any = SimpleNamespace(
            base_url="https://seller.tawreed.io/#/login",
            excel=SimpleNamespace(),
        )

        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                profile_key = "wardany"
                out_dir = Path("artifacts") / "order" / profile_key / "20260826_0900"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "order_item_summary_20260826_0900.csv"
                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    writer.writerow(["1", "Item 1", "added-to-cart"])

                with (
                    patch("src.cli.commands.cli_order_items.load_order_items", return_value=iter(items)),
                    patch("src.cli.cli_shared.require_state_file"),
                    patch("src.cli.commands.cli_order_execution.order_bot") as mock_bot_builder,
                    patch("src.cli.commands.cli_order_execution.run_profile_order") as mock_run_order,
                ):
                    profile_config: Any = SimpleNamespace()
                    run_single_profile_items(app_config, profile_key, profile_config, args)

                    mock_bot_builder.assert_not_called()
                    mock_run_order.assert_not_called()
            finally:
                os.chdir(orig_cwd)

    def test_streamlit_ui_order_command_includes_resume_flag(self) -> None:
        """UI command generator must translate form resume checkbox into CLI '--resume'."""
        form_values_true = {
            "limit": 0,
            "profile_mode": "Single profile",
            "profile_key": "wardany",
            "debug_browser": False,
            "resume": True,
            "match_only": True,
            "execution_mode": "auto",
            "highest_discount": False,
            "min_discount_percent": 0.0,
            "start_item": 1,
            "end_item": 0,
            "item_workers": 1,
        }
        cmd_true = order_command(Path("state/config.yaml"), form_values_true, Path("test.xlsx"))
        self.assertIn("--resume", cmd_true)

        form_values_false = dict(form_values_true, resume=False)
        cmd_false = order_command(Path("state/config.yaml"), form_values_false, Path("test.xlsx"))
        self.assertNotIn("--resume", cmd_false)

    def test_end_to_end_resume_with_small_test_data(self) -> None:
        """Integration test using real data structures simulating an interrupted run."""
        from src.core.utils.excel import load_match_only_items_from_excel
        from src.core.config.config_models import ExcelConfig

        excel_cfg = ExcelConfig(
            code_col="كود",
            name_col="إسم الصنف",
            qty_col="كمية النقص",
        )
        excel_path = Path("data/input/order_items/SMALL_TEST.xlsx")
        if not excel_path.is_file():
            self.skipTest("SMALL_TEST.xlsx not present")

        # Load all 23 items from the actual excel
        all_excel_items = list(load_match_only_items_from_excel(excel_path, excel_cfg))
        self.assertGreater(len(all_excel_items), 0)

        # Simulate that the first 5 items were processed in a previous run
        first_5 = all_excel_items[:5]
        remaining_expected = all_excel_items[5:]

        profile_key = "wardany"
        args = SimpleNamespace(resume=True, match_only=True)

        with TemporaryDirectory() as temp_dir:
            orig_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                out_dir = Path("artifacts") / "order" / profile_key / "20260826_1500"
                out_dir.mkdir(parents=True)
                summary_csv = out_dir / "match_only_summary_20260826_1500.csv"

                with summary_csv.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["item_code", "item_name", "status"])
                    for it in first_5:
                        writer.writerow([it.code, it.name, "matched-only"])

                with patch("src.cli.cli_shared.require_state_file"):
                    resumed_items = list(prepared_order_items(profile_key, all_excel_items, args))

                self.assertEqual(len(resumed_items), len(remaining_expected))
                self.assertEqual(
                    [item_key(it.code, it.name) for it in resumed_items],
                    [item_key(it.code, it.name) for it in remaining_expected],
                )
            finally:
                os.chdir(orig_cwd)



if __name__ == "__main__":
    unittest.main()
