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
