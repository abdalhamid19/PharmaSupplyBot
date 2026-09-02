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


ALNASR_PATH = Path(__file__).parent / "fixtures" / "alnasr.xlsx"
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
            excel_target_path=[f"alnasr={ALNASR_PATH}"],
        )
        selected = selected_excel_target_configs(self.app_config, args)
        self.assertEqual(len(selected), 1)
        target_key, xlsx_paths = selected[0]
        self.assertEqual(target_key, "alnasr")
        self.assertEqual(xlsx_paths, [ALNASR_PATH])

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
            excel_target_path=[f"alnasr={ALNASR_PATH}"],
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        self.assertIn("alnasr", catalogs)
        self.assertGreater(len(catalogs["alnasr"]), 0)

    def test_load_target_catalogs_handles_missing_file(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=["alnasr=data/input/excel target/missing.xlsx"],
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        self.assertEqual(catalogs["alnasr"], [])

    def test_run_excel_target_match_only_persists_run_item_stores(self) -> None:
        """When a run_key is supplied, the match result is written to both
        ``run_items`` (fact) and ``run_item_stores`` (offering snapshot) so
        the Run Results tab can show the Excel candidate alongside any
        Tawreed rows for the same item.
        """
        import sqlite3

        from src.core.database.order_runs_paths import default_order_runs_db
        from src.core.database.order_runs_store import OrderRunsStore

        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=[f"alnasr={ALNASR_PATH}"],
        )
        selected = selected_excel_target_configs(self.app_config, args)
        catalogs = load_target_catalogs(selected, self.app_config)
        items = [Item(code="75865", name="DECLOPHEN GEL30GM.", qty=1)]
        run_key = "test/excel-target-store-rows"
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "summary.csv"
            try:
                run_excel_target_match_only(
                    self.app_config,
                    "alnasr",
                    items,
                    catalogs["alnasr"],
                    summary_path=summary_path,
                    run_key=run_key,
                )
                db = OrderRunsStore(default_order_runs_db()).db
                conn = sqlite3.connect(str(default_order_runs_db()))
                try:
                    fact_rows = conn.execute(
                        "select source_kind, source_label, status from run_items "
                        "where run_key=?",
                        (run_key,),
                    ).fetchall()
                    self.assertEqual(len(fact_rows), 1)
                    fact = fact_rows[0]
                    self.assertEqual(fact[0], "excel-target")
                    self.assertTrue(fact[1].startswith("alnasr@"))
                    self.assertEqual(fact[2], "matched-only")

                    store_rows = conn.execute(
                        "select store_product_id, discount_percent, "
                        "purchase_price, is_winner, source "
                        "from run_item_stores where run_key=?",
                        (run_key,),
                    ).fetchall()
                    self.assertGreaterEqual(len(store_rows), 1)
                    for row in store_rows:
                        self.assertEqual(row[4], "excel_target")
                finally:
                    conn.execute("delete from run_item_stores where run_key=?", (run_key,))
                    conn.execute("delete from run_items where run_key=?", (run_key,))
                    conn.execute("delete from runs where run_key=?", (run_key,))
                    conn.commit()
                    conn.close()
            finally:
                pass

    def test_run_excel_target_match_only_writes_summary(self) -> None:
        args = argparse.Namespace(
            excel_target="alnasr",
            all_excel_targets=False,
            excel_target_path=[f"alnasr={ALNASR_PATH}"],
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
                self.assertEqual(row["source_file"], "alnasr.xlsx")

    def test_multi_path_merges_catalogs_with_source_file(self) -> None:
        """When the same key is fed several files, the CSV records which file
        produced each row."""
        import shutil

        alt_path = ALNASR_PATH.parent / "alnasr_alt.xlsx"
        try:
            shutil.copyfile(ALNASR_PATH, alt_path)
            args = argparse.Namespace(
                excel_target="alnasr",
                all_excel_targets=False,
                excel_target_path=[
                    f"alnasr={ALNASR_PATH}",
                    f"alnasr={alt_path}",
                ],
            )
            selected = selected_excel_target_configs(self.app_config, args)
            self.assertEqual(len(selected), 1)
            target_key, paths = selected[0]
            self.assertEqual(target_key, "alnasr")
            self.assertEqual(len(paths), 2)
            catalogs = load_target_catalogs(selected, self.app_config)
            self.assertEqual(len(catalogs["alnasr"]), 44)
            with tempfile.TemporaryDirectory() as temp_dir:
                summary_path = Path(temp_dir) / "summary.csv"
                items = [Item(code="75865", name="DECLOPHEN GEL30GM.", qty=1)]
                run_excel_target_match_only(
                    self.app_config,
                    "alnasr",
                    items,
                    catalogs["alnasr"],
                    summary_path=summary_path,
                )
                with summary_path.open(newline="", encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
            source_files = {row["source_file"] for row in rows if row["source_file"]}
            self.assertTrue(
                source_files.issubset({"alnasr.xlsx", "alnasr_alt.xlsx"}),
                f"unexpected source_file values: {source_files}",
            )
        finally:
            if alt_path.exists():
                alt_path.unlink()


if __name__ == "__main__":
    unittest.main()