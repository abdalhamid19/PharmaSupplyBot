"""End-to-end persistence and UI-merge tests for Excel-target candidates."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.manual_review.manual_review_candidate_store import (
    append_review_candidates,
    load_review_candidates,
)
from src.core.manual_review.manual_review_candidates import ReviewCandidateOption
from src.ui.manual_review import streamlit_manual_review_page as manual_review_page


def _option(row_key: str, score: float, margin: float) -> ReviewCandidateOption:
    return ReviewCandidateOption(
        store_product_id="same-product-id",
        name_en="VOLTAREN",
        name_ar="فولتارين 3مبول س جديد",
        supplier="excel-target:baraka",
        available_quantity=1,
        price=51.0,
        score=score,
        rejection_reason="candidate requires manual review",
        orderable=True,
        matching_source="excel-target",
        matching_source_label="baraka@محروس1.xlsx",
        target_key="baraka",
        excel_target_key="baraka",
        source_file="محروس1.xlsx",
        excel_target_source_file="محروس1.xlsx",
        identity_evidence_kind="review_identity",
        identity_evidence="review-only anchored Arabic brand expansion",
        compatibility_status="compatible",
        compatibility_rejection="",
        candidate_method="review_identity",
        score_margin=margin,
        shared_brand_tokens=("VOLTAREN",),
        review_status="compatible",
        excel_target_row_key=row_key,
        excel_target_source_row=3100,
        ranking_tier=2,
    )


def test_writer_loader_and_ui_merge_preserve_row_aware_provenance() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir) / "20260911_1700"
        run_dir.mkdir()
        append_review_candidates(
            run_dir,
            "vol3",
            "VOLTAREN 3AMP",
            [_option("row-a", 18.0, 4.5), _option("row-b", 17.5, 3.0)],
        )

        loaded = load_review_candidates(run_dir)
        merged = manual_review_page._load_group_candidates((run_dir,))

        loaded_options = loaded["VOL3::VOLTAREN 3AMP"]
        merged_options = merged["VOL3::VOLTAREN 3AMP"]
        assert {option.excel_target_row_key for option in loaded_options} == {
            "row-a",
            "row-b",
        }
        assert {option.excel_target_row_key for option in merged_options} == {
            "row-a",
            "row-b",
        }
        assert all(option.target_key == "baraka" for option in merged_options)
        assert all(option.source_file == "محروس1.xlsx" for option in merged_options)
        assert {option.candidate_method for option in merged_options} == {
            "review_identity"
        }
        assert {option.ranking_tier for option in merged_options} == {2}
        assert {option.score_margin for option in merged_options} == {4.5, 3.0}
