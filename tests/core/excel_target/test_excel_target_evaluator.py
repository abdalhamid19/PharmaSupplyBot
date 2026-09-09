from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.evaluate_excel_target import evaluate_reports


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gold_labels.csv"


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _base_row(code: str, name: str, **values: str) -> dict[str, str]:
    return {
        "item_code": code,
        "item_name": name,
        "target_key": "baraka",
        "status": "no-results",
        "coverage_category": "identity_absent",
        "candidate_count": "0",
        "review_candidate_count_total": "0",
        "review_candidate_count_saved": "0",
        "manual_review_required": "False",
        "identity_evidence_kind": "",
        "matched_store_product_id": "",
        "candidate_codes": "",
        "compatibility_rejection": "",
        **values,
    }


def test_evaluator_reports_matched_set_and_new_review_items(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    _write_rows(
        before,
        [
            _base_row(
                "1",
                "EXACT 1",
                status="matched-only",
                coverage_category="identity_compatible",
                matched_store_product_id="exact-1",
            ),
            _base_row("2", "UNKNOWN 2"),
        ],
    )
    _write_rows(
        after,
        [
            _base_row(
                "1",
                "EXACT 1",
                status="matched-only",
                coverage_category="identity_compatible",
                matched_store_product_id="exact-1",
            ),
            _base_row(
                "2",
                "UNKNOWN 2",
                coverage_category="excel_target_candidate_available",
                review_candidate_count_total="1",
                review_candidate_count_saved="1",
                manual_review_required="True",
                identity_evidence_kind="review_fuzzy",
                candidate_codes="candidate-2",
            ),
        ],
    )

    report = evaluate_reports(before, after, gold_path=None)

    assert report["matched_set_before"] == [["1", "EXACT 1", "exact-1"]]
    assert report["matched_set_after"] == [["1", "EXACT 1", "exact-1"]]
    assert report["new_review_items"] == [["2", "UNKNOWN 2"]]
    assert report["removed_review_items"] == []


def test_evaluator_validates_independent_gold_labels() -> None:
    rows = [
        _base_row(
            "gold-1",
            "EXACT VERIFIED",
            status="matched-only",
            coverage_category="identity_compatible",
            matched_store_product_id="exact-1",
        ),
        _base_row(
            "gold-2",
            "SAME BRAND DIFFERENT CONCENTRATION",
            coverage_category="excel_target_candidate_available",
            review_candidate_count_total="1",
            review_candidate_count_saved="1",
            manual_review_required="True",
            candidate_codes="strength-variant",
            compatibility_rejection="candidate strength conflicts with requested strength",
        ),
        _base_row(
            "gold-3",
            "SAME BRAND DIFFERENT FORM",
            coverage_category="excel_target_candidate_available",
            review_candidate_count_total="1",
            review_candidate_count_saved="1",
            manual_review_required="True",
            candidate_codes="form-variant",
            compatibility_rejection="candidate form conflicts with requested form",
        ),
        _base_row(
            "gold-4",
            "SAME BRAND DIFFERENT PACK",
            coverage_category="excel_target_candidate_available",
            review_candidate_count_total="1",
            review_candidate_count_saved="1",
            manual_review_required="True",
            candidate_codes="pack-variant",
            compatibility_rejection="candidate pack conflicts with requested pack",
        ),
        _base_row("gold-5", "UNRELATED BRAND"),
        _base_row(
            "gold-6",
            "AMBIGUOUS TWO VARIANT BRAND",
            coverage_category="excel_target_candidate_available",
            review_candidate_count_total="2",
            review_candidate_count_saved="2",
            manual_review_required="True",
            candidate_codes="ambiguous-1;ambiguous-2",
        ),
    ]
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        after = Path(directory) / "after.csv"
        _write_rows(after, rows)
        report = evaluate_reports(after, after, gold_path=FIXTURE_PATH)

    assert report["gold_validation"]["passed"] is True
    assert report["gold_validation"]["failures"] == []


def test_evaluator_flags_review_only_evidence_that_was_auto_matched(
    tmp_path: Path,
) -> None:
    after = tmp_path / "after.csv"
    _write_rows(
        after,
        [
            _base_row(
                "bad-1",
                "FUZZY AUTO",
                status="matched-only",
                coverage_category="identity_compatible",
                identity_evidence_kind="review_fuzzy",
                matched_store_product_id="wrongly-promoted",
            )
        ],
    )

    report = evaluate_reports(after, after, gold_path=None)

    assert any("review_fuzzy" in error for error in report["safety_errors"])


def test_parallel_evaluations_keep_outputs_isolated(tmp_path: Path) -> None:
    before = tmp_path / "before.csv"
    after = tmp_path / "after.csv"
    _write_rows(before, [_base_row("1", "ITEM")])
    _write_rows(after, [_base_row("1", "ITEM")])
    output_paths = [tmp_path / "run-a.json", tmp_path / "run-b.json"]

    def run(output_path: Path) -> Path:
        import json

        report = evaluate_reports(before, after, gold_path=None)
        output_path.write_text(json.dumps(report), encoding="utf-8")
        return output_path

    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = list(executor.map(run, output_paths))

    assert paths == output_paths
    assert all(path.exists() for path in output_paths)
    assert output_paths[0].read_text(encoding="utf-8") == output_paths[1].read_text(
        encoding="utf-8"
    )
