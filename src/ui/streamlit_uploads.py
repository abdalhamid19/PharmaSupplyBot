"""Excel file selection helpers for the Streamlit GUI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .streamlit_shared import ARTIFACTS_DIR, ORDER_ITEMS_DIR


def available_excel_options() -> list[str]:
    """Return the available existing order Excel file choices."""
    if not ORDER_ITEMS_DIR.exists():
        return []
    return [str(path) for path in sorted(ORDER_ITEMS_DIR.glob("*.xlsx"))]


def available_excel_target_options() -> list[str]:
    """Return the available existing Excel target catalog file choices."""
    excel_target_dir = Path("data/input/excel target")
    if not excel_target_dir.exists():
        return []
    return [str(path) for path in sorted(excel_target_dir.glob("*.xlsx"))]


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


def uploaded_excel_target_path(target_key: str, uploaded_file) -> Path:
    """Persist one uploaded Excel target catalog to a stable artifacts path.

    The subprocess that runs the matching CLI is launched with
    ``cwd=PharmaSupplyBot/``. The temporary file is therefore written under
    ``artifacts/uploaded-excel-targets/<key>_<name>.xlsx`` so the subprocess
    can locate it via an absolute path emitted from the GUI.
    """
    uploads_dir = ARTIFACTS_DIR / "uploaded-excel-targets"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(getattr(uploaded_file, "name", f"{target_key}.xlsx")).suffix or ".xlsx"
    safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in target_key)
    target_path = uploads_dir / f"{safe_key}{suffix}"
    target_path.write_bytes(uploaded_file.getvalue())
    return target_path
