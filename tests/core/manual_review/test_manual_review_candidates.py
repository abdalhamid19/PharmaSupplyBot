"""Tests for manual review candidate extraction and JSONL storage."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from src.core.manual_review.manual_review_candidate_store import (
    append_review_candidates,
    load_review_candidates,
)
from src.core.manual_review.manual_review_candidates import (
    ReviewCandidateOption,
    review_candidate_options,
)
from src.core.matching_types import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
)

class ManualReviewCandidatesTests(TestCase):
    def test_extract_options_populates_all_fields_correctly(self) -> None:
        diag = CandidateMatchDiagnostic(
            query="item",
            row_index=0,
            score=15.0,
            sort_key=(15.0,),
            accepted=False,
            accepted_reason="",
            rejection_reason="different_brand",
            breakdown=None,
            candidate={
                "storeProductId": "123",
                "productNameEn": "Name EN",
                "productName": "Name AR",
                "storeName": "Supplier A",
                "availableQuantity": "15",
                "salePrice": "150.5",
            },
        )
        decision = MatchDecision(best_match=None, diagnostics=[diag], final_reason="")
        options = review_candidate_options(decision, limit=5)
        self.assertEqual(len(options), 1)
        opt = options[0]
        self.assertEqual(opt.store_product_id, "123")
        self.assertEqual(opt.name_en, "Name EN")
        self.assertEqual(opt.name_ar, "Name AR")
        self.assertEqual(opt.supplier, "Supplier A")
        self.assertEqual(opt.available_quantity, 15)
        self.assertEqual(opt.price, 150.5)
        self.assertEqual(opt.score, 15.0)
        self.assertEqual(opt.rejection_reason, "different_brand")
        self.assertTrue(opt.orderable)

    def test_extract_options_handles_missing_store_product_id(self) -> None:
        diag = CandidateMatchDiagnostic(
            query="item", row_index=0, score=10.0, sort_key=(10.0,), accepted=False,
            accepted_reason="", rejection_reason="", breakdown=None,
            candidate={"productNameEn": "Test"},
        )
        decision = MatchDecision(best_match=None, diagnostics=[diag], final_reason="")
        options = review_candidate_options(decision)
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].store_product_id, "")
        self.assertFalse(options[0].orderable)

    def test_extract_options_respects_limit(self) -> None:
        diagnostics = [_diag(f"Candidate {idx}", 10.0 - idx, 0.2, 0.2) for idx in range(10)]
        decision = MatchDecision(best_match=None, diagnostics=diagnostics, final_reason="")
        options = review_candidate_options(decision, limit=5)
        self.assertEqual(len(options), 5)

    def test_high_similarity_rejection_is_included_before_low_similarity_top_rows(self):
        wrong = [
            _diag(f"Wrong {idx}", 20.0 - idx, overlap=0.3, sequence=0.3)
            for idx in range(5)
        ]
        correct = _diag(
            "U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM",
            2.5,
            overlap=0.96,
            sequence=0.98,
            exact_bonus=2.0,
        )
        decision = MatchDecision(None, wrong + [correct], "")

        options = review_candidate_options(decision, limit=5)

        self.assertEqual(
            options[0].name_en,
            "U RICHI PANTHENOL ADVANCE CREAM GEL 50 GM",
        )
        self.assertEqual(len(options), 5)

    def test_store_appends_and_loads_candidates(self) -> None:
        options = [
            ReviewCandidateOption(
                store_product_id="s1", name_en="Med", name_ar="ميد",
                supplier="Supp", available_quantity=10, price=20.0,
                score=5.0, rejection_reason="bad", orderable=True
            )
        ]
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "test_run"
            run_dir.mkdir()
            append_review_candidates(run_dir, "C1", "Item One", options)
            append_review_candidates(run_dir, "C2", "Item Two", options)
            loaded = load_review_candidates(run_dir)
            self.assertEqual(len(loaded), 2)
            item_one_key = "C1::ITEM ONE"
            self.assertIn(item_one_key, loaded)
            self.assertEqual(loaded[item_one_key][0].store_product_id, "s1")

    def test_loader_merges_target_candidate_files_and_inherits_source_metadata(self) -> None:
        """One run may contain one JSONL artifact per matching source/target."""
        option = {
            "store_product_id": "baraka-1",
            "name_en": "INODEP 30 CAPS",
            "name_ar": "اينوديب 30 كبسول",
            "supplier": "Baraka",
            "available_quantity": 1,
            "price": 25.0,
            "score": 18.0,
            "rejection_reason": "identity review",
            "orderable": True,
        }
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "20260907_1600"
            run_dir.mkdir()
            for filename, source in (
                ("manual_review_candidates_excel-target_baraka.jsonl", "excel_target"),
                ("manual_review_candidates_tawreed.jsonl", "tawreed"),
            ):
                (run_dir / filename).write_text(
                    json.dumps(
                        {
                            "item_code": "90951",
                            "item_name": "INODEP CAPSULES 30",
                            "options": [option],
                            "source_kind": source,
                            "source_label": "baraka@baraka.xlsx" if source == "excel_target" else "wardany",
                            "target_key": "baraka" if source == "excel_target" else "",
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            loaded = load_review_candidates(run_dir)

        values = loaded["90951::INODEP CAPSULES 30"]
        self.assertEqual(len(values), 2)
        self.assertEqual({value.matching_source for value in values}, {"excel_target", "tawreed"})
        baraka = next(value for value in values if value.matching_source == "excel_target")
        self.assertEqual(baraka.matching_source_label, "baraka@baraka.xlsx")
        self.assertEqual(baraka.target_key, "baraka")

    def test_review_only_provenance_round_trips_and_legacy_fields_default(self) -> None:
        option = ReviewCandidateOption(
            store_product_id="baraka-17",
            name_en="INODEP SYRUP 100 ML",
            name_ar="اينوديب شراب 100 مل",
            supplier="excel-target:baraka",
            available_quantity=1,
            price=10.0,
            score=91.5,
            rejection_reason="form conflict",
            orderable=True,
            matching_source="excel-target",
            target_key="baraka",
            source_file="baraka.xlsx",
            identity_evidence_kind="review_fuzzy",
            candidate_method="english_fuzzy",
            score_margin=8.5,
            shared_brand_tokens=("INODEP",),
            review_status="variant_conflict",
            excel_target_key="baraka",
            excel_target_source_file="baraka.xlsx",
            excel_target_row_key="row-key-17",
            excel_target_source_row=17,
            ranking_tier=3,
        )

        restored = ReviewCandidateOption.from_dict(option.to_dict())
        legacy = ReviewCandidateOption.from_dict(
            {
                "store_product_id": "legacy",
                "name_en": "Legacy",
                "name_ar": "",
                "supplier": "supplier",
                "available_quantity": 1,
                "price": 1.0,
                "score": 1.0,
                "rejection_reason": "",
                "orderable": True,
            }
        )

        self.assertEqual(restored.candidate_method, "english_fuzzy")
        self.assertEqual(restored.review_status, "variant_conflict")
        self.assertEqual(restored.shared_brand_tokens, ("INODEP",))
        self.assertEqual(restored.excel_target_row_key, "row-key-17")
        self.assertEqual(restored.excel_target_source_row, 17)
        self.assertEqual(restored.ranking_tier, 3)
        self.assertEqual(legacy.candidate_method, "")
        self.assertEqual(legacy.review_status, "")
        self.assertEqual(legacy.excel_target_source_row, 0)

    def test_loader_keeps_distinct_excel_rows_with_same_product_identity(self) -> None:
        base = {
            "store_product_id": "duplicate-product",
            "name_en": "DUPLICATE",
            "name_ar": "\u0645\u0643\u0631\u0631",
            "supplier": "excel-target:baraka",
            "available_quantity": 1,
            "price": 10.0,
            "score": 10.0,
            "rejection_reason": "",
            "orderable": True,
            "matching_source": "excel-target",
            "target_key": "baraka",
            "source_file": "baraka.xlsx",
            "candidate_method": "review_identity",
            "ranking_tier": 2,
        }
        with TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "row-key-run"
            run_dir.mkdir()
            rows = []
            for row_key, source_row in (("row-a", 10), ("row-b", 20)):
                option = dict(
                    base,
                    excel_target_row_key=row_key,
                    excel_target_source_row=source_row,
                )
                rows.append(option)
            (run_dir / "manual_review_candidates_excel-target_baraka.jsonl").write_text(
                json.dumps(
                    {
                        "item_key": "1::DUPLICATE",
                        "target_key": "baraka",
                        "source_file": "baraka.xlsx",
                        "options": rows,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = load_review_candidates(run_dir)

        values = loaded["1::DUPLICATE"]
        self.assertEqual(
            {value.excel_target_row_key for value in values}, {"row-a", "row-b"}
        )
        self.assertEqual({value.ranking_tier for value in values}, {2})

def _diag(
    english_name: str,
    score: float,
    overlap: float,
    sequence: float,
    exact_bonus: float = 0.0,
) -> CandidateMatchDiagnostic:
    """Return one rejected diagnostic with a configurable similarity profile."""
    return CandidateMatchDiagnostic(
        query="item", row_index=0, score=score, sort_key=(score,), accepted=False,
        accepted_reason="", rejection_reason="rejected", candidate={
            "storeProductId": f"store-{english_name}",
            "productNameEn": english_name,
        },
        breakdown=MatchScoreBreakdown(
            sequence, overlap, 1.0, exact_bonus, 1.0, 0.0, 0.0, 0.0, score
        ),
    )


if __name__ == "__main__":
    main()
