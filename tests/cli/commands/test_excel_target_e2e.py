"""End-to-end test for the Excel target flow via the registered ``order`` command."""

from __future__ import annotations

import argparse
import csv
import tempfile
import unittest
from pathlib import Path

from src.cli.commands.cli_order_excel_target import (
    load_target_catalogs,
    run_excel_target_match_only,
    selected_excel_target_configs,
)
from src.core.config.config import load_config
from src.core.utils.excel import Item


ALNASR_PATH = Path("data/input/excel target/alnasr.xlsx")
TEST_FIXTURE = Path(__file__).parent / "fixtures" / "excel_target_with_target.yaml"
TEST_EXCEL = Path("data/input/order_items/test_new_feature.xlsx")


class ExcelTargetOrderE2ETests(unittest.TestCase):
    """Drive the Excel target CLI flow against the alnasr catalog."""

    @classmethod
    def setUpClass(cls) -> None:
        if not TEST_FIXTURE.exists():
            TEST_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
            TEST_FIXTURE.write_text(
                """site:
  base_url: "https://example.test"
excel:
  code_col: "كود"
  name_col: "إسم الصنف"
  qty_col: "كمية النقص"
profiles:
  wardany:
    display_name: "Wardany"
excel_targets:
  alnasr:
    display_name: "Alnasr"
    name_col: "صنف"
    price_col: "سعر"
    discount_col: "الخصم"
""",
                encoding="utf-8",
            )
        if not ALNASR_PATH.exists():
            raise unittest.SkipTest(f"Alnasr catalog missing at {ALNASR_PATH}")
        cls.app_config = load_config(TEST_FIXTURE)

    def test_selected_excel_target_configs_resolves_alnasr(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=None,
        )
        selected = selected_excel_target_configs(self.app_config, args)
        self.assertEqual(len(selected), 1)
        target_key, xlsx_path = selected[0]
        self.assertEqual(target_key, "alnasr")
        self.assertEqual(xlsx_path, ALNASR_PATH)

    def test_selected_excel_target_configs_all(self) -> None:
        args = argparse.Namespace(
            excel_target=None,
            all_excel_targets=True,
            excel_target_path=None,
        )
        selected = selected_excel_target_configs(self.app_config, args)
        self.assertEqual([key for key, _ in selected], ["alnasr"])

    def test_selected_excel_target_configs_none(self) -> None:
        args = argparse.Namespace(
            excel_target=None,
            all_excel_targets=False,
            excel_target_path=None,
        )
        selected = selected_excel_target_configs(self.app_config, args)
        self.assertEqual(selected, [])

    def test_load_target_catalogs_reads_alnasr(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=None,
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        self.assertIn("alnasr", catalogs)
        self.assertGreater(len(catalogs["alnasr"]), 0)

    def test_load_target_catalogs_handles_missing_file(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path="alnasr=data/input/excel target/missing.xlsx",
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        self.assertEqual(catalogs["alnasr"], [])

    def test_run_excel_target_match_only_writes_summary(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=None,
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        items = [
            Item(code="75865", name="DECLOPHEN GEL30GM.", qty=1),
            Item(code="90235", name="ANDOPENTENE 300MG 30TAB", qty=1),
            Item(code="90697", name="MAPI PLUS 20CAP", qty=1),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.csv"
            totals = run_excel_target_match_only(
                self.app_config,
                "alnasr",
                items,
                catalogs["alnasr"],
                summary_path=summary_path,
            )
            self.assertEqual(totals["processed"], 3)
            self.assertEqual(totals["matched"], 3)
            self.assertEqual(totals["flagged"], 0)
            self.assertTrue(summary_path.exists())
            with summary_path.open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 3)
            for row in rows:
                self.assertEqual(row["target_kind"], "excel-target")
                self.assertEqual(row["target_key"], "alnasr")


if __name__ == "__main__":
    unittest.main()