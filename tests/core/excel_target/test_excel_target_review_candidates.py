"""Focused tests for Excel-target manual-review candidate extraction."""

from __future__ import annotations

from unittest import TestCase

from src.core.config.config_models import MatchingConfig
from src.core.excel_target import (
    ExcelTargetReviewCandidate,
    ExcelTargetMatcher,
    TargetProduct,
)
from src.core.excel_target.excel_target_identity import IdentityEvidence
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.excel_target.product_attributes import validate_product_compatibility
from src.core.utils.excel import Item


class ExcelTargetReviewCandidateTests(TestCase):
    def test_candidates_are_target_rows_with_variant_rejection_metadata(self) -> None:
        matcher = ExcelTargetMatcher(
            "baraka",
            [
                TargetProduct(
                    "syrup",
                    "INODEP SYRUP 100 ML",
                    42.0,
                    5.0,
                    source_file="baraka.xlsx",
                ),
                TargetProduct(
                    "capsules",
                    "INODEP CAPSULES 30",
                    55.0,
                    5.0,
                    source_file="baraka.xlsx",
                ),
            ],
        )

        result = matcher.match(
            Item(code="1", name="INODEP CAPSULES 30", qty=1), MatchingConfig()
        )

        self.assertEqual(result.decision.best_match.data["storeProductId"], "capsules")
        self.assertEqual(len(result.review_candidates), 2)
        rejected = next(
            candidate
            for candidate in result.review_candidates
            if candidate.product.code == "syrup"
        )
        self.assertFalse(rejected.compatibility.accepted)
        self.assertEqual(rejected.compatibility_status, "rejected")
        self.assertIn("form", rejected.compatibility_rejection)
        self.assertEqual(rejected.source_kind, "excel-target")
        self.assertEqual(rejected.source_label, "baraka@baraka.xlsx")

    def test_incompatible_target_candidate_is_available_when_match_is_rejected(self) -> None:
        matcher = ExcelTargetMatcher(
            "baraka",
            [TargetProduct("syrup", "INODEP SYRUP 100 ML", 42.0, 5.0)],
        )

        result = matcher.match(
            Item(code="1", name="INODEP CAPSULES 30", qty=1), MatchingConfig()
        )

        self.assertIsNone(result.decision.best_match)
        self.assertEqual(len(result.review_candidates), 1)
        candidate = result.review_candidates[0]
        self.assertEqual(candidate.product.code, "syrup")
        self.assertFalse(candidate.compatibility.accepted)
        self.assertIn("form", candidate.rejection_reason)

    def test_adapter_exposes_only_target_product_fields(self) -> None:
        candidate = ExcelTargetReviewCandidate(
            target_key="baraka",
            product=TargetProduct(
                "capsules",
                "INODEP CAPSULES 30",
                55.0,
                5.0,
                source_file="baraka.xlsx",
            ),
            score=19.4,
            compatibility=validate_product_compatibility(
                "INODEP CAPSULES 30", "INODEP CAPSULES 30"
            ),
        )

        data = candidate.to_review_candidate_dict()
        self.assertEqual(data["store_product_id"], "capsules")
        self.assertEqual(data["matching_source"], "excel-target")
        self.assertEqual(data["target_key"], "baraka")
        self.assertEqual(data["source_file"], "baraka.xlsx")
        self.assertEqual(data["compatibility_status"], "compatible")
        self.assertNotIn("tawreed", str(data).lower())

    def test_review_candidate_persists_fuzzy_provenance_and_stable_row_identity(self) -> None:
        product = TargetProduct(
            "inodep-17",
            "INODEP SYRUP 100 ML",
            42.0,
            5.0,
            source_file="Baraka\\catalog.xlsx",
            source_row_number=17,
        )
        candidate = ExcelTargetReviewCandidate(
            target_key="baraka",
            product=product,
            score=91.5,
            compatibility=validate_product_compatibility(
                "INODEP CAPSULES 30", product.name_ar
            ),
            identity_evidence=IdentityEvidence(
                "review_fuzzy",
                "INODEP",
                "english fuzzy candidate",
                0.915,
            ),
            rejection_reason="form: TABLET vs SYRUP",
            candidate_method="english_fuzzy",
            score_margin=8.5,
            shared_brand_tokens=("INODEP",),
        )

        data = candidate.to_review_candidate_dict()

        self.assertEqual(data["identity_evidence_kind"], "review_fuzzy")
        self.assertEqual(data["candidate_method"], "english_fuzzy")
        self.assertEqual(data["score_margin"], 8.5)
        self.assertEqual(data["shared_brand_tokens"], ("INODEP",))
        self.assertEqual(data["review_status"], "variant_conflict")
        self.assertEqual(data["excel_target_source_row"], 17)
        self.assertEqual(
            data["excel_target_row_key"], excel_target_row_key("baraka", product)
        )

    def test_stable_row_key_distinguishes_duplicate_codes_and_rows(self) -> None:
        first = TargetProduct(
            "duplicate",
            "INODEP 20 CAPS",
            1.0,
            0.0,
            source_file="baraka.xlsx",
            source_row_number=17,
        )
        second = TargetProduct(
            "duplicate",
            "INODEP 30 CAPS",
            1.0,
            0.0,
            source_file="baraka.xlsx",
            source_row_number=18,
        )

        self.assertNotEqual(
            excel_target_row_key("baraka", first),
            excel_target_row_key("baraka", second),
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
