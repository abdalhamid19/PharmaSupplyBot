"""Regression tests for Excel-target Manual Review artifacts."""

from __future__ import annotations

import csv
import json
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src.cli.commands import cli_order_excel_target
from src.core.artifact_run import ArtifactRun
from src.core.config.config import load_config
from src.core.excel_target.excel_target_review_discovery import ReviewDiscoveryHit
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatch
from src.core.excel_target.excel_target_review_candidates import (
    ExcelTargetReviewCandidate,
)
from src.core.excel_target.excel_target_identity import IdentityEvidence
from src.core.manual_review.manual_review_store import ManualReviewStore
from src.core.utils.excel import Item
from src.core.matching_types import MatchDecision
from src.core.excel_target.product_attributes import validate_product_compatibility


class ExcelTargetManualReviewArtifactTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config(
            Path("tests/cli/commands/fixtures/excel_target_with_target.yaml")
        )

    def _run_with_temp_artifacts(self, catalog, item):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact_root = root

            @contextmanager
            def fake_artifact_run(command, profile_key, run_id=None, root=None):
                run = ArtifactRun(
                    command, profile_key, run_id or "test-run", root=artifact_root
                )
                run.directory.mkdir(parents=True, exist_ok=True)
                yield run

            with patch.object(cli_order_excel_target, "artifact_run", fake_artifact_run):
                result = cli_order_excel_target.run_excel_target_match_only(
                    self.config,
                    "alnasr",
                    [item],
                    catalog,
                    summary_path=root / "summary.csv",
                    run_id="test-run",
                )
            run_dir = root / "excel-target" / "alnasr" / "test-run"
            review_path = run_dir / "manual_review_excel-target_alnasr.csv"
            candidates_path = (
                run_dir / "manual_review_candidates_excel-target_alnasr.jsonl"
            )
            return (
                result,
                review_path.read_text(encoding="utf-8") if review_path.exists() else "",
                candidates_path.read_text(encoding="utf-8")
                if candidates_path.exists()
                else "",
            )

    def test_rejected_target_candidate_creates_review_artifacts(self) -> None:
        arabic_name = "\u0627\u064a\u0646\u0648\u062f\u064a\u0628 \u0634\u0631\u0627\u0628 100 \u0645\u0644"
        arabic_brand = "\u0627\u064a\u0646\u0648\u062f\u064a\u0628"
        catalog = [
            TargetProduct("inodep-syrup", arabic_name, 10.0, 0.0, "baraka.xlsx")
        ]
        item = Item("90951", "INODEP CAPSULES 30", 1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": arabic_brand, "en": "INODEP"}],
        ):
            totals, review_text, candidates_text = self._run_with_temp_artifacts(
                catalog, item
            )

        self.assertEqual(totals["manual_review"], 1)
        self.assertTrue(review_text)
        self.assertTrue(candidates_text)
        row = next(csv.DictReader(review_text.splitlines()))
        self.assertEqual(row["manual_review_required"], "True")
        self.assertEqual(row["matching_source"], "excel-target")
        self.assertEqual(row["candidate_count"], "1")
        payload = json.loads(candidates_text)
        self.assertEqual(payload["source_kind"], "excel-target")
        self.assertEqual(payload["options"][0]["compatibility_status"], "rejected")
        self.assertIn("form", payload["options"][0]["compatibility_rejection"])

    def test_no_identity_candidate_does_not_enter_manual_review(self) -> None:
        catalog = [
            TargetProduct(
                "unknown-row",
                "\u0639\u0644\u0627\u062c \u0645\u062c\u0647\u0648\u0644 \u0634\u0631\u0627\u0628",
                10.0,
                0.0,
                "baraka.xlsx",
            )
        ]
        item = Item("90952", "UNKNOWN BRAND CAPSULES 30", 1)
        totals, review_text, candidates_text = self._run_with_temp_artifacts(catalog, item)
        self.assertEqual(totals["manual_review"], 0)
        self.assertEqual(review_text, "")
        self.assertEqual(candidates_text, "")

    def test_identity_absent_with_discovery_candidate_enters_manual_review(self) -> None:
        catalog = [
            TargetProduct(
                "unknown-row",
                "\u0639\u0644\u0627\u062c \u0645\u062c\u0647\u0648\u0644 \u0634\u0631\u0627\u0628",
                10.0,
                0.0,
                "baraka.xlsx",
                source_row_number=44,
            )
        ]
        item = Item("90953", "UNKNOWN BRAND CAPSULES 30", 1)
        discovery_hit = ReviewDiscoveryHit(
            product=catalog[0],
            score=94.0,
            runner_up_score=70.0,
            score_margin=24.0,
            strategy="english_fuzzy",
            review_status="strong",
            shared_brand_tokens=("UNKNOWN",),
            attribute_note="",
        )
        with patch(
            "src.core.excel_target.excel_target_review_discovery."
            "ExcelTargetReviewDiscoveryIndex.discover",
            return_value=(discovery_hit,),
        ):
            totals, review_text, candidates_text = self._run_with_temp_artifacts(
                catalog, item
            )

        self.assertEqual(totals["manual_review"], 1)
        self.assertTrue(review_text)
        self.assertTrue(candidates_text)
        row = next(csv.DictReader(review_text.splitlines()))
        self.assertEqual(row["manual_review_required"], "True")
        self.assertEqual(row["manual_review_category"], "excel_target_candidate_available")
        payload = json.loads(candidates_text)
        self.assertEqual(payload["options"][0]["candidate_method"], "english_fuzzy")
        self.assertEqual(payload["options"][0]["excel_target_source_row"], 44)

    def test_total_candidates_are_distinct_from_saved_candidate_cap(self) -> None:
        catalog = [
            TargetProduct(
                f"row-{index}",
                f"\u0635\u0646\u0641 \u062a\u062c\u0631\u064a\u0628\u064a {index}",
                10.0 + index,
                0.0,
                "baraka.xlsx",
                source_row_number=index,
            )
            for index in range(1, 5)
        ]
        item = Item("90954", "TEST BRAND 30", 1)
        compatibility = validate_product_compatibility(item.name, catalog[0].name_ar)
        candidates = tuple(
            ExcelTargetReviewCandidate(
                target_key="alnasr",
                product=product,
                score=90.0 - index,
                compatibility=compatibility,
                identity_evidence=IdentityEvidence(
                    "review_identity",
                    "test",
                    "test-only review identity",
                    0.9,
                ),
                candidate_method="review_identity",
            )
            for index, product in enumerate(catalog)
        )
        match = ExcelTargetMatch(
            "alnasr",
            MatchDecision(None, [], "test review candidates"),
            len(catalog),
            candidates,
        )
        with patch.object(
            cli_order_excel_target.ExcelTargetMatcher,
            "match",
            return_value=match,
        ), patch.object(
            cli_order_excel_target,
            "_review_candidate_limit",
            return_value=2,
        ):
            _totals, review_text, candidates_text = self._run_with_temp_artifacts(
                catalog, item
            )

        row = next(csv.DictReader(review_text.splitlines()))
        self.assertEqual(row["candidate_count_total"], "4")
        self.assertEqual(row["candidate_count_saved"], "2")
        payload = json.loads(candidates_text)
        self.assertEqual(payload["candidate_count_total"], 4)
        self.assertEqual(payload["candidate_count_saved"], 2)
        self.assertEqual(len(payload["options"]), 2)

    def test_auto_matched_excel_target_records_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            item = Item("1", "INODEP CAPSULES 30", 1)
            best = {
                "storeProductId": "baraka-1",
                "productNameEn": "INODEP 30 CAPS",
                "productName": "INODEP 30 CAPS",
                "identity_evidence_kind": "dictionary",
                "identity_evidence": "dictionary direct hit",
            }
            with patch.object(cli_order_excel_target, "DEFAULT_MANUAL_REVIEW_DB", db_path):
                cli_order_excel_target._auto_save_excel_target_match(
                    self.config,
                    item,
                    best,
                    target_key="alnasr",
                    source_file="baraka.xlsx",
                    run_id="run-1",
                )
            saved = ManualReviewStore(db_path).lookup("1", "INODEP CAPSULES 30")

        self.assertIsNotNone(saved)
        assert saved is not None
        self.assertEqual(saved.manual_decision, "auto_matched")
        self.assertEqual(saved.matching_source, "excel-target")
        self.assertEqual(saved.matching_source_label, "alnasr@baraka.xlsx")
        self.assertEqual(saved.excel_target_key, "alnasr")

    def test_tawreed_decision_does_not_block_excel_target_auto_save(self) -> None:
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "manual.sqlite3"
            store = ManualReviewStore(db_path)
            item = Item("1", "INODEP CAPSULES 30", 1)
            store.upsert(
                cli_order_excel_target.ManualReviewDecision(
                    item_code=item.code,
                    item_name=item.name,
                    approved=True,
                    correct_store_product_id="tawreed-1",
                    manual_decision="approved_match",
                    matching_source="tawreed",
                    matching_source_label="wardany",
                )
            )
            best = {
                "storeProductId": "baraka-1",
                "productNameEn": "INODEP 30 CAPS",
                "productName": "INODEP 30 CAPS",
            }
            with patch.object(cli_order_excel_target, "DEFAULT_MANUAL_REVIEW_DB", db_path):
                cli_order_excel_target._auto_save_excel_target_match(
                    self.config,
                    item,
                    best,
                    target_key="alnasr",
                    source_file="baraka.xlsx",
                    run_id="run-1",
                )

            rows = store.lookup_all(item.code, item.name)

        self.assertEqual(len(rows), 2)
        self.assertEqual({row.matching_source for row in rows}, {"tawreed", "excel-target"})
