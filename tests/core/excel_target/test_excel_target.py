"""Unit tests for the Excel target loader and matching engine."""

from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from src.core.config.config_models import (
    ExcelTargetConfig,
    MatchingConfig,
)
from src.core.excel_target import (
    ExcelTargetMatch,
    TargetProduct,
    find_best_match_in_target,
    first_accepted_match,
    load_target_catalog_from_excel,
    match_item_against_all_targets,
)
from src.core.utils.excel import Item


DATA_ROOT = Path("data/input/excel target")
ALNASR_PATH = DATA_ROOT / "alnasr.xlsx"


def _build_catalog() -> list[TargetProduct]:
    config = ExcelTargetConfig(
        name_col="صنف",
        price_col="سعر",
        discount_col="الخصم",
    )
    return load_target_catalog_from_excel(ALNASR_PATH, config)


class TestExcelTargetLoader(TestCase):
    """Tests for the Excel target catalog loader."""

    def setUp(self) -> None:
        self.catalog = _build_catalog()

    def test_loads_alnasr_catalog(self) -> None:
        self.assertEqual(len(self.catalog), 22)
        first = self.catalog[0]
        self.assertEqual(first.name, "AMIGRAINE  ADCO 30TAB")
        self.assertEqual(first.price, 51.0)
        self.assertEqual(first.discount_percent, 1.0)

    def test_empty_rows_are_skipped(self) -> None:
        for product in self.catalog:
            self.assertTrue(product.name)
            self.assertGreaterEqual(product.price, 0)
            self.assertGreaterEqual(product.discount_percent, 0)

    def test_missing_file_raises(self) -> None:
        config = ExcelTargetConfig(
            name_col="صنف", price_col="سعر", discount_col="الخصم"
        )
        with self.assertRaises(FileNotFoundError):
            load_target_catalog_from_excel(Path("missing.xlsx"), config)

    def test_target_product_to_candidate_dict(self) -> None:
        product = TargetProduct(
            code="ABC",
            name="DECLOPHEN GEL",
            price=55.0,
            discount_percent=2.0,
        )
        candidate = product.to_candidate_dict()
        self.assertEqual(candidate["productNameEn"], "DECLOPHEN GEL")
        self.assertEqual(candidate["availableQuantity"], 1)
        self.assertEqual(candidate["discountPercent"], 2.0)
        self.assertEqual(candidate["salePrice"], 55.0)
        self.assertTrue(candidate["excelTarget"])


class TestExcelTargetMatching(TestCase):
    """Tests for the Excel target matching engine."""

    def setUp(self) -> None:
        self.catalog = _build_catalog()
        self.matching_config = MatchingConfig()

    def test_declophen_matches_alnasr(self) -> None:
        item = Item(code="75865", name="DECLOPHEN GEL30GM.", qty=1)
        match = find_best_match_in_target(
            item, "alnasr", self.catalog, self.matching_config
        )
        self.assertIsInstance(match, ExcelTargetMatch)
        self.assertIsNotNone(match.decision.best_match)
        self.assertIn(
            "DECLOPHEN",
            match.decision.best_match.data["productNameEn"].upper(),
        )

    def test_no_match_returns_decision_with_reason(self) -> None:
        catalog = [
            TargetProduct(
                code="X1",
                name="PARACETAMOL 500MG TAB",
                price=10.0,
                discount_percent=1.0,
            )
        ]
        item = Item(code="999", name="UNKNOWN_BRAND XYZ 100MG", qty=1)
        match = find_best_match_in_target(
            item, "test", catalog, self.matching_config
        )
        self.assertIsNone(match.decision.best_match)
        self.assertEqual(match.catalog_size, 1)
        self.assertTrue(match.decision.final_reason)

    def test_empty_catalog_returns_empty_decision(self) -> None:
        item = Item(code="1", name="PARACETAMOL", qty=1)
        match = find_best_match_in_target(
            item, "empty", [], self.matching_config
        )
        self.assertIsNone(match.decision.best_match)
        self.assertEqual(
            match.decision.final_reason, "Excel target catalog is empty."
        )

    def test_match_against_all_targets_returns_per_target_decisions(self) -> None:
        item = Item(code="1", name="MAPI PLUS 20CAP", qty=1)
        catalogs = {"alnasr": self.catalog}

        from src.core.config.config_models import (
            AppConfig,
            DatabaseConfig,
            ExcelConfig,
            RuntimeConfig,
        )

        app_config = AppConfig(
            base_url="",
            excel=ExcelConfig(
                code_col="كود", name_col="إسم الصنف", qty_col="كمية النقص"
            ),
            profiles={},
            selectors={},
            warehouse_strategy={},
            matching=self.matching_config,
            runtime=RuntimeConfig(),
            database=DatabaseConfig(),
        )
        results = match_item_against_all_targets(item, app_config, catalogs)
        self.assertIn("alnasr", results)
        self.assertIsNotNone(results["alnasr"].decision.best_match)
        first = first_accepted_match(results)
        self.assertIsNotNone(first)
        target_key, accepted = first
        self.assertEqual(target_key, "alnasr")
        self.assertIsNotNone(accepted.decision.best_match)


class TestConfigExcelTargets(TestCase):
    """Tests for the AppConfig excel_targets wiring."""

    def test_load_config_with_excel_targets(self) -> None:
        from src.core.config.config import load_config

        yaml_path = Path(__file__).parent / "fixtures" / "with_excel_targets.yaml"
        config = load_config(yaml_path)
        self.assertIn("alnasr", config.excel_targets)
        alnasr = config.excel_targets["alnasr"]
        self.assertEqual(alnasr.name_col, "صنف")
        self.assertEqual(alnasr.price_col, "سعر")
        self.assertEqual(alnasr.discount_col, "الخصم")
        self.assertTrue(alnasr.enabled)
        self.assertEqual(list(config.enabled_excel_targets().keys()), ["alnasr"])

    def test_excel_targets_to_run_validation(self) -> None:
        from src.core.config.config import load_config

        yaml_path = Path(__file__).parent / "fixtures" / "with_excel_targets.yaml"
        config = load_config(yaml_path)
        selected = config.excel_targets_to_run(
            excel_target="alnasr", all_excel_targets=False
        )
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0], "alnasr")

        with self.assertRaises(Exception):
            config.excel_targets_to_run(
                excel_target="missing", all_excel_targets=False
            )

        all_selected = config.excel_targets_to_run(
            excel_target=None, all_excel_targets=True
        )
        self.assertEqual([key for key, _ in all_selected], ["alnasr"])