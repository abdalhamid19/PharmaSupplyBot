"""Excel file selection helpers for the Streamlit GUI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .streamlit_shared import INPUT_DIR


def available_excel_options() -> list[str]:
    """Return the available existing Excel file choices."""
    if not INPUT_DIR.exists():
        return []
    return [str(path) for path in sorted(INPUT_DIR.glob("*.xlsx"))]


def resolve_excel_path(excel_path_str: object, uploaded_file) -> Path | None:
    """Return a usable Excel path from an existing file or uploaded content."""
    if uploaded_file is not None:
        return uploaded_excel_path(uploaded_file)
    if excel_path_str:
        return Path(str(excel_path_str))
    return None


def uploaded_excel_path(uploaded_file) -> Path:
    """Persist one uploaded Excel file to a temporary path and return it."""
    suffix = Path(uploaded_file.name).suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getvalue())
        return Path(temp_file.name)
