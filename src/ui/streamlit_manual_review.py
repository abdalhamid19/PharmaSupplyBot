"""Manual-review learning controls for Streamlit result runs."""

from __future__ import annotations

from pathlib import Path

from .streamlit_manual_review_editor import render_manual_review_editor as _render_editor
from .streamlit_manual_review_persistence import _render_action_sections
from .streamlit_manual_review_rows import editable_manual_review_rows
from .streamlit_manual_review_data import (
    save_manual_review_rows,
    manual_review_decisions_from_rows,
)


def render_manual_review_editor(rows: list[dict[str, str]], run_dir: Path) -> None:
    """Render editable manual-review decisions and persist approved corrections."""
    edited_records = _render_editor(rows, run_dir)
    _render_action_sections(edited_records, run_dir)


__all__ = [
    "render_manual_review_editor",
    "editable_manual_review_rows",
    "save_manual_review_rows",
    "manual_review_decisions_from_rows",
]
