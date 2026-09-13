"""Unit tests for the Excel target loader and matching engine."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import openpyxl

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
from src.core.excel_target.excel_target_identity import ExcelTargetBilingualIndex
from src.core.utils.excel import Item


DATA_ROOT = Path("data/input/excel target")
ALNASR_PATH = Path(__file__).resolve().parent / "fixtures" / "alnasr.xlsx"


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
        self.assertEqual(candidate["price"], 55.0)
        self.assertTrue(candidate["excelTarget"])
        self.assertEqual(candidate["priceMeaning"], "public_with_discount")

    def test_blank_price_stays_unknown_while_zero_price_stays_zero(self) -> None:
        """Empty price cells must not become synthetic zero-price offers."""
        with TemporaryDirectory() as temp:
            path = Path(temp) / "prices.xlsx"
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.append(["Name", "Price", "Discount"])
            sheet.append(["BLANK PRICE", None, None])
            sheet.append(["ZERO PRICE", 0, 0])
            workbook.save(path)
            workbook.close()

            products = load_target_catalog_from_excel(
                path,
                ExcelTargetConfig(
                    name_col="Name", price_col="Price", discount_col="Discount"
                ),
            )

        self.assertEqual([product.price for product in products], [None, 0.0])
        blank_candidate = products[0].to_candidate_dict()
        zero_candidate = products[1].to_candidate_dict()
        self.assertNotIn("price", blank_candidate)
        self.assertEqual(zero_candidate["price"], 0.0)

    def test_target_product_purchase_only_uses_saleprice_key(self) -> None:
        """Purchase-only catalog exposes ``salePrice`` so the matcher reads it."""
        product = TargetProduct(
            code="ABC",
            name="DECLOPHEN GEL",
            price=55.0,
            discount_percent=0.0,
            price_meaning="purchase_only",
        )
        candidate = product.to_candidate_dict()
        self.assertEqual(candidate["salePrice"], 55.0)
        self.assertNotIn("price", candidate)

    def test_target_product_records_source_file(self) -> None:
        product = TargetProduct(
            code="ABC",
            name="DECLOPHEN GEL",
            price=55.0,
            discount_percent=2.0,
            source_file="warehouse_1.xlsx",
        )
        self.assertEqual(product.source_file, "warehouse_1.xlsx")
        candidate = product.to_candidate_dict()
        self.assertEqual(candidate["excelTargetSourceFile"], "warehouse_1.xlsx")


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
        self.assertEqual(
            alnasr.aliases,
            ({"en": "LEVOFLOXACIN-EVA", "ar": "ليفوفلوكساسين ايفا 500مجم 10اقراص", "source": "fixture"},),
        )
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


class TestBilingualOfflineEvidence(TestCase):
    """Bilingual offline evidence verifies Arabic catalog rows safely."""

    def test_cached_bilingual_evidence_qualifies_arabic_candidate(self) -> None:
        """Inodep in Arabic matches when offline translation cache confirms INODEP."""
        from unittest.mock import patch
        item = Item(code="90951", name="INODEP CAPSULES 30", qty=1)
        catalog = [
            TargetProduct(
                code="inodp-ar",
                name="اينوديب 30 كبسول",
                price=50.0,
                discount_percent=5.0,
            ),
            TargetProduct(
                code="unrelated-30",
                name="سالبوفنت 30 قرص",
                price=20.0,
                discount_percent=0.0,
            ),
        ]
        cfg = MatchingConfig(
            enable_bilingual_secondary_match=True,
            bilingual_min_score=0.75,
        )
        with patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={
                catalog[0].name: "INODEP 30 CAPSULES",
                catalog[1].name: "SALBOVENT 30 TABLETS",
            },
        ):
            match = find_best_match_in_target(item, "test", catalog, cfg)
            self.assertIsNotNone(match)
            self.assertIsNotNone(match.decision.best_match)
            self.assertEqual(match.decision.best_match.data["storeProductId"], "inodp-ar")
            self.assertTrue(match.decision.best_match.data.get("verified_brand_identity"))

    def test_unrelated_arabic_row_remains_unmatched_even_with_shared_numbers(self) -> None:
        """Salbovent 30 tablets never matches INODEP 30 even with bilingual match enabled."""
        from unittest.mock import patch
        item = Item(code="90951", name="INODEP CAPSULES 30", qty=1)
        catalog = [
            TargetProduct(
                code="unrelated-30",
                name="سالبوفنت 30 قرص",
                price=20.0,
                discount_percent=0.0,
            )
        ]
        cfg = MatchingConfig(
            enable_bilingual_secondary_match=True,
            bilingual_min_score=0.75,
        )
        with patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={catalog[0].name: "SALBOVENT 30 TABLETS"},
        ):
            match = find_best_match_in_target(item, "test", catalog, cfg)
            self.assertIsNotNone(match)
            self.assertIsNone(match.decision.best_match)


class TestExcelTargetIdentityTranslationFallback(TestCase):
    def test_dictionary_identity_precedes_live_translation(self) -> None:
        arabic_name = "براند قاموسي 30 كبسول"
        catalog = [TargetProduct("dictionary-row", arabic_name, 50.0, 0.0)]

        with (
            patch(
                "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
                return_value={"rows": []},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.load_dictionary",
                return_value={
                    "by_en": {
                        "DICTIONARYBRAND": [
                            {"ar": "براند قاموسي", "en": "DICTIONARYBRAND"}
                        ]
                    }
                },
            ),
            patch(
                "src.core.excel_target.excel_target_identity.lookup_en",
                return_value=[{"ar": "براند قاموسي", "en": "DICTIONARYBRAND"}],
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
                return_value={},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many",
                return_value={arabic_name: "DICTIONARYBRAND 30 CAPSULES"},
            ) as live_translation,
        ):
            index = ExcelTargetBilingualIndex.build(
                catalog,
                allow_live_translation=True,
            )

        live_translation.assert_not_called()
        identified = index.identify("DICTIONARYBRAND CAPSULES 30")
        self.assertEqual(len(identified), 1)
        self.assertEqual(identified[0].evidence.kind, "dictionary")

    def test_tawreed_identity_precedes_live_translation(self) -> None:
        arabic_name = "اينوديب 30 كبسول"
        catalog = [TargetProduct("tawreed-row", arabic_name, 50.0, 0.0)]

        with (
            patch(
                "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
                return_value={
                    "rows": [{"ar": arabic_name, "en": "INODEP 30 CAPS"}]
                },
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
                return_value={},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many",
                return_value={arabic_name: "INODEP 30 CAPSULES"},
            ) as live_translation,
        ):
            index = ExcelTargetBilingualIndex.build(
                catalog,
                allow_live_translation=True,
            )

        live_translation.assert_not_called()
        identified = index.identify("INODEP CAPSULES 30")
        self.assertEqual(len(identified), 1)
        self.assertEqual(identified[0].evidence.kind, "tawreed_catalog")

    def test_index_can_disable_live_translation_deterministically(self) -> None:
        arabic_name = "اسم عربي غير مخزن"
        catalog = [TargetProduct("offline-row", arabic_name, 50.0, 0.0)]

        with (
            patch(
                "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
                return_value={"rows": []},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
                return_value={},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many",
            ) as live_translation,
        ):
            index = ExcelTargetBilingualIndex.build(
                catalog,
                allow_live_translation=False,
            )

        live_translation.assert_not_called()
        self.assertEqual(index.identify("UNKNOWN BRAND"), ())

    def test_index_uses_stable_batch_translation_api_for_unresolved_names(self) -> None:
        arabic_name = "براند غير معروف 30 كبسول"
        catalog = [
            TargetProduct(
                code="cohere-row",
                name=arabic_name,
                price=50.0,
                discount_percent=0.0,
            )
        ]

        with (
            patch(
                "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
                return_value={"rows": []},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.lookup_en",
                return_value=[],
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
                return_value={},
            ),
            patch(
                "src.core.excel_target.excel_target_identity.ar_to_en_many",
                return_value={arabic_name: "MYSTERYBRAND 30 CAPSULES"},
            ) as live_translation,
        ):
            index = ExcelTargetBilingualIndex.build(
                catalog,
                allow_live_translation=True,
            )

        live_translation.assert_called_once_with([arabic_name])
        identified = index.identify("MYSTERYBRAND CAPSULES 30")
        self.assertEqual(len(identified), 1)
        self.assertEqual(identified[0].product.code, "cohere-row")
        self.assertEqual(identified[0].evidence.kind, "cohere_translation")


class TestExcelTargetStableRowIdentity(TestCase):
    """Regression tests for deterministic Excel-row candidate identities."""

    def test_loaded_products_record_their_excel_row_number(self) -> None:
        catalog = _build_catalog()

        self.assertEqual(catalog[0].source_row_number, 2)
        self.assertEqual(catalog[-1].source_row_number, 23)

    def test_code_less_id_is_sha256_of_normalized_source_row_and_name(self) -> None:
        import hashlib

        product = TargetProduct(
            code="",
            name="  BRAND   NAME  ",
            price=10.0,
            discount_percent=0.0,
            source_file=r"Warehouse\Catalog.xlsx",
            source_row_number=12,
        )

        expected_material = "warehouse/catalog.xlsx|12|brand name"
        expected_id = hashlib.sha256(
            expected_material.encode("utf-8")
        ).hexdigest()
        self.assertEqual(product.store_product_id, expected_id)
        self.assertEqual(len(product.store_product_id), 64)

    def test_code_less_id_is_stable_and_distinguishes_source_rows_and_files(self) -> None:
        product = TargetProduct(
            code="",
            name="BRAND NAME",
            price=10.0,
            discount_percent=0.0,
            source_file="catalog.xlsx",
            source_row_number=12,
        )
        same_row_rebuilt = TargetProduct(
            code="",
            name="BRAND NAME",
            price=99.0,
            discount_percent=5.0,
            source_file="catalog.xlsx",
            source_row_number=12,
        )
        different_row = TargetProduct(
            code="",
            name="BRAND NAME",
            price=10.0,
            discount_percent=0.0,
            source_file="catalog.xlsx",
            source_row_number=13,
        )
        different_file = TargetProduct(
            code="",
            name="BRAND NAME",
            price=10.0,
            discount_percent=0.0,
            source_file="another_catalog.xlsx",
            source_row_number=12,
        )

        self.assertEqual(product.store_product_id, same_row_rebuilt.store_product_id)
        self.assertNotEqual(product.store_product_id, different_row.store_product_id)
        self.assertNotEqual(product.store_product_id, different_file.store_product_id)

    def test_explicit_code_remains_primary_identity(self) -> None:
        first = TargetProduct(
            code="DUPLICATE-CODE",
            name="FIRST VARIANT",
            price=10.0,
            discount_percent=0.0,
            source_file="catalog.xlsx",
            source_row_number=12,
        )
        second = TargetProduct(
            code="DUPLICATE-CODE",
            name="SECOND VARIANT",
            price=12.0,
            discount_percent=0.0,
            source_file="catalog.xlsx",
            source_row_number=13,
        )

        self.assertEqual(first.store_product_id, "DUPLICATE-CODE")
        self.assertEqual(second.store_product_id, "DUPLICATE-CODE")

    def test_existing_positional_constructor_keeps_raw_argument_and_safe_default(self) -> None:
        product = TargetProduct(
            "legacy-code",
            "LEGACY PRODUCT",
            10.0,
            0.0,
            "legacy.xlsx",
            {"name": "LEGACY PRODUCT"},
        )

        self.assertEqual(product.raw, {"name": "LEGACY PRODUCT"})
        self.assertEqual(product.source_row_number, 0)
        self.assertEqual(product.store_product_id, "legacy-code")

    def test_code_less_candidates_keep_distinct_stable_ids(self) -> None:
        products = [
            TargetProduct(
                code="",
                name="SAME PRODUCT",
                price=10.0,
                discount_percent=0.0,
                source_file="catalog.xlsx",
                source_row_number=12,
            ),
            TargetProduct(
                code="",
                name="SAME PRODUCT",
                price=11.0,
                discount_percent=0.0,
                source_file="catalog.xlsx",
                source_row_number=13,
            ),
        ]

        candidates = [product.to_candidate_dict() for product in products]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            len({candidate["storeProductId"] for candidate in candidates}),
            2,
        )


class TestExcelTargetDigitBearingBrands(TestCase):
    def test_brand_digits_are_not_erased_from_identity(self) -> None:
        from src.core.excel_target.excel_target_identity import normalize_english_brand

        self.assertEqual(normalize_english_brand("VITAMIN B12 30 TAB"), "VITAMIN B12")
        self.assertEqual(normalize_english_brand("7UP 250 ML"), "7UP")
        self.assertNotEqual(
            normalize_english_brand("VITAMIN B12"),
            normalize_english_brand("VITAMIN B6"),
        )

    def test_arabic_brand_digits_are_not_erased(self) -> None:
        from src.core.excel_target.excel_target_identity import normalize_arabic_brand

        self.assertNotEqual(
            normalize_arabic_brand("فيتامين ب12"),
            normalize_arabic_brand("فيتامين ب6"),
        )
