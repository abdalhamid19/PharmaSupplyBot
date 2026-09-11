from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tools.report_excel_target_candidate_coverage import build_report


def _write_artifact(root: Path, *, duplicate: bool = False, invalid: bool = False) -> Path:
    root.mkdir()
    summary = root / "match_only_summary_target.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "item_code",
                "item_name",
                "candidate_count_total",
                "candidate_count",
                "manual_review_required",
                "manual_review_category",
                "candidate_count_displayed",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "item_code": "1",
                "item_name": "TEST ITEM",
                "candidate_count_total": "3",
                "candidate_count": "2",
                "manual_review_required": "True",
                "manual_review_category": "excel_target_candidate_available",
                "candidate_count_displayed": "",
            }
        )
        writer.writerow(
            {
                "item_code": "2",
                "item_name": "NO CANDIDATE",
                "candidate_count_total": "0",
                "candidate_count": "0",
                "manual_review_required": "False",
                "manual_review_category": "identity_absent",
                "candidate_count_displayed": "",
            }
        )

    record = {
        "item_key": "1::TEST ITEM",
        "candidate_count_total": 3,
        "candidate_count_saved": 2 if not invalid else 4,
        "options": [
            {
                "candidate_method": "review_identity",
                "excel_target_row_key": "row-1",
            },
            {
                "candidate_method": "review_identity_prefix",
                "excel_target_row_key": "row-2",
            },
        ],
    }
    candidates = root / "manual_review_candidates_excel-target_target.jsonl"
    with candidates.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
        if duplicate:
            handle.write(json.dumps(record) + "\n")
    return root


def test_report_separates_generated_saved_and_unmeasured_display(tmp_path: Path) -> None:
    artifact = _write_artifact(tmp_path / "run")
    report = build_report([artifact])
    metrics = report["reports"][0]

    assert metrics["candidate_generated_total"] == 3
    assert metrics["candidate_union_total"] == 3
    assert metrics["candidate_saved_total"] == 2
    assert metrics["candidate_displayed_total"] is None
    assert metrics["candidate_count_total_distribution"]["p95"] == 3
    assert metrics["candidate_count_total_distribution"]["max"] == 3
    assert metrics["candidate_budget"]["status"] == "pass"
    assert metrics["precision_sample"]["status"] == "labels_not_provided"


def test_report_fails_candidate_budget_thresholds(tmp_path: Path) -> None:
    artifact = _write_artifact(tmp_path / "run")

    report = build_report(
        [artifact], candidate_p99_limit=2, candidate_max_limit=2
    )

    budget = report["reports"][0]["candidate_budget"]
    assert budget["status"] == "fail"
    assert "candidate_count_generated.p99=3 > 2" in budget["violations"]
    assert "candidate_count_generated.max=3 > 2" in budget["violations"]


def test_report_rejects_duplicate_item_records(tmp_path: Path) -> None:
    artifact = _write_artifact(tmp_path / "run", duplicate=True)
    with pytest.raises(ValueError, match="duplicate item_key"):
        build_report([artifact])


def test_report_rejects_saved_count_above_generated_count(tmp_path: Path) -> None:
    artifact = _write_artifact(tmp_path / "run", invalid=True)
    with pytest.raises(ValueError, match="invalid candidate counts"):
        build_report([artifact])


def test_report_accepts_gold_schema_and_excludes_uncertain_labels(tmp_path: Path) -> None:
    artifact = _write_artifact(tmp_path / "run")
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "item_code,item_name,expected_row_key,label\n"
        "1,TEST ITEM,row-1,P\n"
        "1,TEST ITEM,row-2,N_variant\n"
        "1,TEST ITEM,row-3,U\n",
        encoding="utf-8",
    )

    report = build_report([artifact], labels)
    precision = report["reports"][0]["precision_sample"]

    assert precision["status"] == "computed"
    assert precision["positive_candidates"] == 1
    assert precision["negative_candidates"] == 1
    assert precision["uncertain_candidates"] == 0
    assert precision["precision_percent"] == 50.0
    assert precision["precision_interval_percent"]["lower_percent"] < 50.0
    assert precision["precision_interval_percent"]["upper_percent"] > 50.0
    assert precision["recall_at_saved_percent"] == 100.0
    assert precision["recall_at_saved_interval_percent"]["upper_percent"] == 100.0
