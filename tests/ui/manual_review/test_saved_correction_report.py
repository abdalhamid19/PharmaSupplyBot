"""Regression tests for the artifact-only approved-correction audit boundary."""

from __future__ import annotations

from pathlib import Path


PAGE = Path("src/ui/manual_review/streamlit_manual_review_page_saved.py")


def test_saved_corrections_page_does_not_render_counterfactual_report() -> None:
    """Saved Corrections must stay focused on decisions, not audit artifacts."""
    source = PAGE.read_text(encoding="utf-8")

    assert "_render_latest_approved_correction_report" not in source
    assert "_latest_approved_correction_report" not in source
    assert "approved_correction_report" not in source
    assert "Approved correction audit" not in source

