"""Safety and performance contracts for Arabic Excel-target matching."""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.matching_types import DecisionSource
from src.core.utils.excel import Item
from src.core.normalization.translation import CachedTranslations


ITEM = Item(code="90951", name="INODEP CAPSULES 30", qty=1)


class TestBarakaSafeMatching(TestCase):
    def _matcher(self, *names: str) -> ExcelTargetMatcher:
        products = [
            TargetProduct(str(index), name, 10.0, 0.0)
            for index, name in enumerate(names, start=1)
        ]
        return ExcelTargetMatcher("baraka", products)

    def test_dictionary_identity_requires_matching_form_strength_and_pack(self) -> None:
        """A verified brand cannot override a contradictory product variant."""
        matcher = self._matcher(
            "اينوديب شراب 100 مل",
            "اينوديب 1000 مجم 30 كبسول",
            "اينوديب 20 كبسول",
            "اينوديب 30 كبسول",
        )
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": "اينوديب", "en": "INODEP"}],
        ):
            decision = matcher.match(ITEM, MatchingConfig()).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["storeProductId"], "4")
        self.assertEqual(
            decision.best_match.data["identity_evidence_kind"], "tawreed_catalog"
        )
        self.assertEqual(decision.best_match.data["compatibility_status"], "compatible")

    def test_arabic_only_rows_never_claim_to_be_english(self) -> None:
        product = TargetProduct("1", "اينوديب 30 كبسول", 10.0, 0.0)
        candidate = product.to_candidate_dict()
        self.assertEqual(candidate["productName"], "اينوديب 30 كبسول")
        self.assertEqual(candidate["productNameEn"], "")
        self.assertFalse(candidate["verified_brand_identity"])

    def test_excel_target_never_calls_tawreed_fuzzy_matcher(self) -> None:
        matcher = self._matcher("اينوديب 30 كبسول")
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": "اينوديب", "en": "INODEP"}],
        ), patch(
            "src.core.normalization.bilingual_brand_matcher.match_brand_readonly",
            side_effect=AssertionError("Tawreed matching must not be called"),
        ):
            self.assertIsNotNone(matcher.match(ITEM, MatchingConfig()).decision.best_match)

    def test_index_is_built_once_for_many_items(self) -> None:
        matcher = self._matcher("INODEP CAPSULES 30")
        index_id = id(matcher.identity_index)
        for _ in range(50):
            matcher.match(ITEM, MatchingConfig())
        self.assertEqual(id(matcher.identity_index), index_id)

    def test_identity_sources_are_loaded_once_per_matcher_session(self) -> None:
        with patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ) as cached_lookup, patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": []},
        ) as tawreed_loader:
            matcher = self._matcher("اينوديب 30 كبسول")
            for _ in range(50):
                matcher.match(ITEM, MatchingConfig())

        cached_lookup.assert_called_once()
        tawreed_loader.assert_called_once_with()

    def test_tawreed_catalog_alias_can_identify_target_row_without_live_translation(self) -> None:
        """A verified Tawreed alias may identify an existing Baraka row safely."""
        matcher = self._matcher("اينوديب 30 كبسول")
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {
                        "ar": "اينوديب 30 كبسول",
                        "en": "INODEP 30 CAPS",
                    }
                ]
            },
        ):
            decision = matcher.match(ITEM, MatchingConfig()).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["identity_evidence_kind"], "tawreed_catalog")
        self.assertEqual(decision.best_match.data["storeProductId"], "1")

    def test_safe_policy_keeps_cohere_only_identity_for_manual_review(self) -> None:
        arabic_name = "براند غير معروف 30 كبسول"
        with patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": []},
        ), patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ), patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many",
            return_value={arabic_name: "MYSTERYBRAND 30 CAPSULES"},
        ):
            matcher = ExcelTargetMatcher(
                "baraka",
                [TargetProduct("cohere-row", arabic_name, 50.0, 0.0)],
                allow_live_translation=True,
            )

        match = matcher.match(
            Item(code="mystery", name="MYSTERYBRAND CAPSULES 30", qty=1),
            MatchingConfig(),
        )

        self.assertIsNone(match.decision.best_match)
        self.assertIn("Cohere", match.decision.final_reason)
        self.assertTrue(match.review_candidates)

    def test_cached_cohere_identity_remains_manual_review_only(self) -> None:
        arabic_name = "براند غير معروف 30 كبسول"
        cached = CachedTranslations(
            {arabic_name: "MYSTERYBRAND 30 CAPSULES"},
            {arabic_name: "command-a-translate-08-2025"},
        )
        with patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": []},
        ), patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ), patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value=cached,
        ):
            matcher = ExcelTargetMatcher(
                "baraka",
                [TargetProduct("cached-row", arabic_name, 50.0, 0.0)],
            )

        match = matcher.match(
            Item(code="mystery", name="MYSTERYBRAND CAPSULES 30", qty=1),
            MatchingConfig(),
        )

        self.assertIsNone(match.decision.best_match)
        self.assertIn("Cohere", match.decision.final_reason)

    def test_safe_alias_typo_matches_only_after_variant_compatibility(self) -> None:
        target_name = "اكسومايلين الترا 600 مجم 30 قرص"
        with patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {
                        "en": "AXOMYELIN ULTRA 600 MG 30 TAB",
                        "ar": target_name,
                    }
                ]
            },
        ), patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ), patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ):
            matcher = ExcelTargetMatcher(
                "baraka",
                [TargetProduct("target", target_name, 50.0, 0.0)],
            )

        decision = matcher.match(
            Item(code="90266", name="AXOMYELIN ULLTRA 30TAB 600MG", qty=1),
            MatchingConfig(),
        ).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["identity_evidence_kind"], "safe_alias"
        )

    def test_tawreed_alias_keeps_all_target_variants_for_compatibility_filtering(self) -> None:
        """An alias must not discard another target row before variant checks."""
        matcher = self._matcher(
            "اينوديب 20 كبسول",
            "اينوديب 30 كبسول",
        )
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {"ar": "اينوديب 20 كبسول", "en": "INODEP 20 CAPS"},
                    {"ar": "اينوديب 30 كبسول", "en": "INODEP 30 CAPS"},
                ]
            },
        ):
            decision = matcher.match(ITEM, MatchingConfig()).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["storeProductId"], "2")

    def test_legacy_manual_review_cannot_force_an_excel_target_match(self) -> None:
        matcher = self._matcher("اينوديب شراب 100 مل")
        legacy = ManualReviewDecision(ITEM.code, ITEM.name, True, "1")
        with patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=legacy,
        ):
            self.assertIsNone(matcher.match(ITEM, MatchingConfig()).decision.best_match)

    def test_scoped_manual_review_cannot_override_variant_safety(self) -> None:
        matcher = self._matcher("اينوديب شراب 100 مل")
        scoped = ManualReviewDecision(
            ITEM.code, ITEM.name, True, "1", excel_target_key="baraka"
        )
        with patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=scoped,
        ) as saved_lookup, patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind_failure"
        ):
            best = matcher.match(ITEM, MatchingConfig()).decision.best_match
        self.assertIsNone(best)
        saved_lookup.assert_called_once_with(
            ITEM,
            matching_source="excel-target",
            excel_target_key="baraka",
            include_legacy=False,
        )

    def test_approved_match_rebinds_to_current_file_code_for_same_target(self) -> None:
        matcher = ExcelTargetMatcher(
            "baraka",
            [TargetProduct("new-code", "INODEP CAPSULES 30", 10, 0, "new.xlsx")],
        )
        scoped = ManualReviewDecision(
            ITEM.code,
            ITEM.name,
            True,
            "old-code",
            correct_product_name="INODEP CAPSULES 30",
            manual_decision="approved_match",
            excel_target_key="baraka",
            excel_target_source_file="old.xlsx",
            matching_source="excel-target",
            matching_source_label="baraka@old.xlsx",
        )
        with patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=scoped,
        ), patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind"
        ) as record:
            decision = matcher.match(ITEM, MatchingConfig()).decision

        best = decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "new-code")
        self.assertEqual(best.data["identity_evidence_kind"], "manual_review_rebound")
        self.assertEqual(decision.source, DecisionSource.MANUAL_REVIEW_SAVED)
        record.assert_called_once()

    def test_scoped_approved_match_can_override_saved_variant_conflict(self) -> None:
        """A human approval may intentionally select a different product variant."""
        product = TargetProduct(
            "target",
            "DANTRELAX 25 MG 30 CAPS",
            10,
            0,
            "baraka.xlsx",
            source_row_number=7,
        )
        matcher = ExcelTargetMatcher("baraka", [product])
        scoped = ManualReviewDecision(
            "dantrelax",
            "DANTRELAX 30 CAP",
            True,
            "target",
            correct_product_name="DANTRELAX 25 MG 30 CAPS",
            manual_decision="approved_match",
            excel_target_key="baraka",
            excel_target_source_file="baraka.xlsx",
            excel_target_row_key=excel_target_row_key("baraka", product),
            excel_target_source_row=7,
            matching_source="excel-target",
            matching_source_label="baraka@baraka.xlsx",
        )
        with patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=scoped,
        ), patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind"
        ) as record:
            decision = matcher.match(
                Item(code="dantrelax", name="DANTRELAX 30 CAP", qty=1),
                MatchingConfig(),
            ).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.source, DecisionSource.MANUAL_REVIEW_SAVED)
        self.assertEqual(
            decision.best_match.data["compatibility_status"],
            "approved_manual_override",
        )
        self.assertTrue(decision.best_match.data["manual_override"])
        self.assertIn("approved_manual_override", decision.final_reason)
        record.assert_called_once()

    def test_stale_scoped_approval_does_not_block_current_discovery(self) -> None:
        product = TargetProduct(
            "current",
            "INODEP CAPSULES 30",
            10,
            0,
            "new.xlsx",
            source_row_number=9,
        )
        matcher = ExcelTargetMatcher("baraka", [product])
        stale = ManualReviewDecision(
            ITEM.code,
            ITEM.name,
            True,
            "old",
            correct_product_name="INODEP CAPSULES 30",
            manual_decision="approved_match",
            excel_target_key="baraka",
            excel_target_source_file="old.xlsx",
            excel_target_row_key="old-row",
            excel_target_source_row=2,
            matching_source="excel-target",
        )
        with patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=stale,
        ), patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind_failure"
        ):
            decision = matcher.match(ITEM, MatchingConfig()).decision

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["storeProductId"], "current")

    def test_non_approved_target_decisions_remain_manual_across_excel_files(self) -> None:
        matcher = ExcelTargetMatcher(
            "baraka",
            [TargetProduct("new-code", "INODEP CAPSULES 30", 10, 0, "new.xlsx")],
        )
        for status in ("not_matching", "needs_correction"):
            scoped = ManualReviewDecision(
                ITEM.code,
                ITEM.name,
                False,
                manual_decision=status,
                excel_target_key="baraka",
                excel_target_source_file="old.xlsx",
                matching_source="excel-target",
            )
            with self.subTest(status=status), patch(
                "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
                return_value=scoped,
            ):
                decision = matcher.match(ITEM, MatchingConfig()).decision
                self.assertIsNone(decision.best_match)
                self.assertIn(status, decision.final_reason)

    def test_pantogar_packaging_suffix_does_not_hide_verified_brand(self) -> None:
        matcher = self._matcher("بانتوجار 6شريط 60 كبسولة س ج")
        item = Item(code="90431", name="PANTOGAR 60 CAP", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": "بانتوجار 60 كبسول", "en": "PANTOGAR"}],
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")

    def test_augram_catalog_suffix_does_not_hide_verified_brand(self) -> None:
        matcher = self._matcher("اوجرام 1جرام 14قرص س ج")
        item = Item(code="82690", name="AUGRAM 1 GM 14 TAB", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": "أوجرام", "en": "AUGRAM"}],
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")

    def test_avetrix_arabic_gel_variant_keeps_verified_brand(self) -> None:
        matcher = self._matcher("افيتركس جيل ملين ومرطب 100جم")
        item = Item(code="74870", name="AVETRIX GEL 100 G", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[{"ar": "افيتركس جل 100 جم", "en": "AVETRIX"}],
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")

    def test_aggrex_reviewed_arabic_spelling_variant_is_safe(self) -> None:
        matcher = self._matcher("اجركس 75 مجم 60 قرص س ق")
        item = Item(code="63136", name="AGGREX 75 MG 60 TAB", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {"ar": "اجريكس 75 مجم 60 اقراص", "en": "AGGREX 75 MG 60 TAB"}
                ]
            },
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")
        self.assertEqual(best.data["identity_evidence_kind"], "tawreed_catalog")

    def test_alphintern_reviewed_arabic_spelling_variant_is_safe(self) -> None:
        matcher = self._matcher("الفنترن 30قرص س ج")
        item = Item(code="alp", name="ALPHINTERN 30 F.C. TABS.", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {"ar": "الفينترن 30 اقراص", "en": "ALPHINTERN 30 F.C. TABS"}
                ]
            },
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")
        self.assertEqual(best.data["identity_evidence_kind"], "tawreed_catalog")

    def test_bivatracin_tawreed_alias_matches_existing_spray_row(self) -> None:
        matcher = self._matcher("بيفاتراسين سبراى")
        item = Item(code="73894", name="BIVATRACIN SPRAY", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {
                        "ar": "بيفاتراسين 150 مجم بخاخ",
                        "en": "BIVATRACIN AEROSOL POWDER 150 GM",
                    }
                ]
            },
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "1")
        self.assertEqual(best.data["identity_evidence_kind"], "tawreed_catalog")

    def test_asmakast_reviewed_arabic_spelling_variant_selects_matching_strength(self) -> None:
        matcher = self._matcher(
            "ازماكاست 5 مجم 30 قرص",
            "ازماكست 10 مجم 30 قرص س ج",
        )
        item = Item(code="81464", name="ASMAKAST 10 MG 30 TAB", qty=1)
        with patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ), patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ), patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {"ar": "ازماكاست 10 مجم 30 اقراص", "en": "ASMAKAST 10 MG 30 TAB"}
                ]
            },
        ):
            best = matcher.match(item, MatchingConfig()).decision.best_match
        self.assertIsNotNone(best)
        self.assertEqual(best.data["storeProductId"], "2")
        self.assertEqual(best.data["identity_evidence_kind"], "tawreed_catalog")
