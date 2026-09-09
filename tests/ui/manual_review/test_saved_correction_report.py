"""Contract tests for the read-only approved-correction audit view."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from src.ui.manual_review.streamlit_manual_review_page_saved import (
    _approved_correction_report_view_model,
    _latest_approved_correction_report,
    _render_approved_correction_report,
)


def _report() -> dict:
    return {
        "schema_version": "approved-correction-report.v1",
        "target_catalog_fingerprint": "abc123",
        "counts_by_root_cause": {
            "identity_absent": 2,
            "variant_conflict": 1,
        },
        "counts": {
            "automatic_verified": 4,
            "approved_manual_override": 3,
            "stale_or_invalid": 1,
        },
        "findings": [
            {
                "item_code": "100",
                "item_name": "AMOXICILLIN 500",
                "target_key": "baraka",
                "row_key": "baraka:12:abc",
                "approval_status": "stale",
                "root_cause": "stale_row_key",
                "excel_target_source_file": r"C:\private\state\manual_review.db",
                "counterfactual_status": "no_match",
                "counterfactual_reason": "identity absent",
            },
            {
                "item_code": "101",
                "item_name": "PARACETAMOL 500",
                "target_key": "baraka",
                "row_key": "baraka:13:def",
                "approval_status": "applied",
                "root_cause": "identity_absent",
                "counterfactual_status": "no_match",
            },
        ],
        "recommendations": [
            {
                "root_cause": "identity_absent",
                "evidence_count": 2,
                "sample_item_keys": ["100::AMOXICILLIN 500"],
                "requires_human_approval": True,
            }
        ],
    }


def test_view_model_exposes_root_cause_counts_and_stale_approvals_without_paths() -> None:
    view = _approved_correction_report_view_model(_report())

    assert view["root_cause_counts"] == {
        "identity_absent": 2,
        "variant_conflict": 1,
    }
    assert len(view["stale_approvals"]) == 1
    assert view["stale_approvals"][0]["item_code"] == "100"
    rendered = json.dumps(view, ensure_ascii=False)
    assert "manual_review.db" not in rendered
    assert "C:\\private" not in rendered


def test_latest_report_uses_newest_json_for_selected_target(tmp_path: Path) -> None:
    older = tmp_path / "excel-target" / "baraka" / "20260909_0900"
    newer = tmp_path / "excel-target" / "baraka" / "20260909_1000"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    old_path = older / "approved_correction_report_baraka.json"
    new_path = newer / "approved_correction_report_baraka.json"
    old_path.write_text("{}", encoding="utf-8")
    new_path.write_text("{}", encoding="utf-8")

    assert _latest_approved_correction_report(tmp_path, "baraka") == new_path


def test_render_report_is_read_only_and_has_no_apply_rule_action() -> None:
    class _Expander:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    with patch(
        "src.ui.manual_review.streamlit_manual_review_page_saved.st"
    ) as streamlit:
        streamlit.expander.return_value = _Expander()
        _render_approved_correction_report(_report())

    streamlit.button.assert_not_called()
    labels = [call.args[0] for call in streamlit.metric.call_args_list]
    assert any("identity_absent" in label for label in labels)

