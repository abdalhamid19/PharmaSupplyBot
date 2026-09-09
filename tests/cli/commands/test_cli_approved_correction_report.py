"""Contract tests for the read-only approved-correction report adapter."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from openpyxl import Workbook

from src.cli.commands.cli_approved_correction_report import (
    run_approved_correction_report_command,
)
from src.core.config.config_models import ExcelTargetConfig, MatchingConfig
from src.core.errors import ValidationError


class ApprovedCorrectionReportCommandTests(TestCase):
    def test_writes_versioned_json_and_utf8_sig_csv_without_upsert(self) -> None:
        with self.subTest("artifacts"):
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                workbook = root / "baraka.xlsx"
                _write_catalog(workbook)
                db_path = root / "manual.sqlite3"
                _create_read_only_fixture_db(db_path)
                output = root / "reports"
                app_config = _app_config()
                report = SimpleNamespace(
                    findings=(
                        SimpleNamespace(
                            item_code="1",
                            item_name="PANADOL 500",
                            target_key="baraka",
                            row_key="baraka.xlsx:2",
                            excel_target_source_file="baraka.xlsx",
                            excel_target_source_row=2,
                            approval_run_id="run-1",
                            catalog_fingerprint="abc",
                            approval_status="applied",
                            counterfactual_status="rejected",
                            root_cause="identity_absent",
                            original_reason="no identity",
                            counterfactual_reason="no identity",
                            final_reason="manual",
                            compatibility_status="compatible",
                            candidate_method="identity",
                            candidate_count_total=1,
                            decision_source="saved_correction",
                            match_origin="approved_manual_override",
                        ),
                    ),
                    counts_by_root_cause={"identity_absent": 1},
                    recommendations=(),
                )

                with patch(
                    "src.cli.commands.cli_approved_correction_report.analyze_approved_corrections",
                    return_value=report,
                ), patch(
                    "src.core.manual_review.manual_review_store.ManualReviewStore.upsert",
                    side_effect=AssertionError("report generation must not upsert"),
                ) as upsert:
                    result = run_approved_correction_report_command(
                        app_config,
                        SimpleNamespace(
                            excel_target=["baraka"],
                            excel_target_path=[f"baraka={workbook}"],
                            output=str(output),
                            manual_review_db=str(db_path),
                        ),
                    )

                self.assertEqual(result, 0)
                upsert.assert_not_called()
                json_path = output / "approved_correction_report.json"
                csv_path = output / "approved_correction_findings.csv"
                payload = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], 1)
                self.assertEqual(payload["findings"][0]["match_origin"], "approved_manual_override")
                self.assertEqual(len(payload["target_catalog_fingerprints"]["baraka"]), 64)
                self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["root_cause"], "identity_absent")

    def test_rejects_duplicate_target_keys_and_missing_paths(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_config = _app_config()
            duplicate = SimpleNamespace(
                excel_target=["baraka", "baraka"],
                excel_target_path=[],
                output=str(root / "reports"),
                manual_review_db=str(root / "manual.sqlite3"),
            )
            with self.assertRaises(ValidationError):
                run_approved_correction_report_command(app_config, duplicate)

            missing = SimpleNamespace(
                excel_target=["baraka"],
                excel_target_path=[f"baraka={root / 'missing.xlsx'}"],
                output=str(root / "reports"),
                manual_review_db=str(root / "manual.sqlite3"),
            )
            with self.assertRaises(ValidationError):
                run_approved_correction_report_command(app_config, missing)


def _write_catalog(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "price", "discount"])
    sheet.append(["PANADOL 500", 10, 0])
    workbook.save(path)


def _create_read_only_fixture_db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "create table manual_review_decisions ("
            "item_code text, item_name text, approved integer, "
            "correct_store_product_id text, manual_decision text, "
            "correct_product_name text, correct_product_name_ar text, "
            "correct_query text, run_id text, excel_target_key text, "
            "excel_target_source_file text, matching_source text, "
            "matching_source_label text, identity_evidence_kind text, "
            "identity_evidence text, supplier_scope_key text, "
            "last_rebind_status text, excel_target_row_key text, "
            "excel_target_source_row integer, candidate_method text, "
            "review_status text)"
        )
        connection.execute(
            "insert into manual_review_decisions values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("1", "PANADOL 500", 1, "baraka-1", "approved_match", "", "", "", "run-1", "baraka", "baraka.xlsx", "excel-target", "baraka@baraka.xlsx", "", "", "baraka", "", "baraka.xlsx:2", 2, "identity", "",),
        )


def _app_config() -> SimpleNamespace:
    return SimpleNamespace(
        excel_targets={
            "baraka": ExcelTargetConfig(
                name_col="name",
                price_col="price",
                discount_col="discount",
            )
        },
        matching=MatchingConfig(),
    )
