"""Read-only tests for the real manual-review display boundary."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.manual_review.manual_review_candidates import ReviewCandidateOption
from src.core.manual_review.manual_review_store import ManualReviewDecision
from tools.measure_excel_target_c_display import (
    build_report,
    measure_display,
    read_explicit_saved_counts,
)


def _option(
    product_id: str,
    *,
    row_key: str = "",
    source: str = "excel-target",
    target: str = "baraka",
) -> ReviewCandidateOption:
    return ReviewCandidateOption(
        store_product_id=product_id,
        name_en=f"PRODUCT {product_id}",
        name_ar="",
        supplier=target,
        available_quantity=1,
        price=10.0,
        score=10.0,
        rejection_reason="review",
        orderable=True,
        matching_source=source,
        matching_source_label=f"{target}@catalog.xlsx",
        target_key=target,
        excel_target_key=target,
        source_file="catalog.xlsx",
        excel_target_row_key=row_key,
        candidate_method="review_identity",
        ranking_tier=2,
    )


def _write_record(run_dir: Path, item_code: str, item_name: str, options, **extra) -> None:
    payload = {
        "item_key": f"{item_code}::{item_name.upper()}",
        "item_code": item_code,
        "item_name": item_name,
        "candidate_count_saved": len(options),
        "options": [option.to_dict() for option in options],
        **extra,
    }
    path = run_dir / "manual_review_candidates_fixture.jsonl"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")


def test_saved_count_is_explicit_and_has_no_fallback() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        _write_record(run_dir, "C1", "Item One", [_option("1"), _option("2")])
        result = read_explicit_saved_counts((run_dir,))
        assert result.status == "measured"
        assert result.count == 2

        missing = run_dir / "manual_review_candidates_missing.jsonl"
        missing.write_text(
            json.dumps({"item_key": "C2::ITEM TWO", "options": [{"x": 1}]}) + "\n",
            encoding="utf-8",
        )
        result = read_explicit_saved_counts((run_dir,))
        assert result.status == "not_measured"
        assert result.count is None


def test_saved_count_mismatch_is_inconsistent() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        path = Path(temp_dir) / "manual_review_candidates_bad.jsonl"
        path.write_text(
            json.dumps(
                {
                    "item_key": "C1::ITEM ONE",
                    "candidate_count_saved": 3,
                    "options": [_option("1").to_dict(), _option("2").to_dict()],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = read_explicit_saved_counts((run_dir,))
        assert result.status == "inconsistent"
        assert result.count is None


def test_display_measurement_captures_source_limit_and_row_keys() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        options = [_option(str(index), row_key=f"row-{index}") for index in range(4)]
        _write_record(run_dir, "C1", "Item One", options)

        result = measure_display((run_dir,), display_limit=3)

        assert result["c_loaded_unique"] == 4
        assert result["c_display_run"] == 3
        assert result["captured"][0]["row_keys"] == ["row-0", "row-1", "row-2"]
        assert result["invariants"]["passed"]


def test_display_measurement_paginates_51_items_without_loss_or_duplication() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        for index in range(51):
            _write_record(run_dir, f"C{index}", f"Item {index}", [_option(str(index))])

        result = measure_display((run_dir,), display_limit=5)

        assert result["c_loaded_unique"] == 51
        assert result["c_display_run"] == 51
        assert result["c_display_pages"] == [50, 1]
        assert result["displayed_items"] == 51
        assert len({record["item_key"] for record in result["captured"]}) == 51


def test_display_measurement_keeps_same_product_on_distinct_excel_rows() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        _write_record(
            run_dir,
            "C1",
            "Item One",
            [_option("same", row_key="row-a"), _option("same", row_key="row-b")],
        )

        result = measure_display((run_dir,), display_limit=5)

        assert result["c_loaded_unique"] == 2
        assert result["c_display_run"] == 2
        assert result["captured"][0]["row_keys"] == ["row-a", "row-b"]


def test_hide_completed_changes_display_only_and_keeps_saved_count() -> None:
    with TemporaryDirectory() as temp_dir:
        run_dir = Path(temp_dir)
        _write_record(
            run_dir,
            "C1",
            "Item One",
            [_option("baraka-1", row_key="row-a"), _option("baraka-2", row_key="row-b")],
        )
        decision = ManualReviewDecision(
            item_code="C1",
            item_name="ITEM ONE",
            approved=True,
            matching_source="excel-target",
            excel_target_key="baraka",
        )

        baseline = build_report((run_dir,), display_limit=5)
        hidden = build_report(
            (run_dir,),
            display_limit=5,
            hide_completed=True,
            decisions={("C1", "ITEM ONE"): [decision]},
        )

        assert baseline["targets"][0]["c_saved_artifact"] == 2
        assert hidden["targets"][0]["c_saved_artifact"] == 2
        assert baseline["targets"][0]["c_display_run"] == 2
        assert hidden["targets"][0]["c_display_run"] == 0
