"""Profile artifact management functions for results tab."""

from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

from .streamlit_shared import ARTIFACTS_DIR


def clear_profile_result_data(profile_key: str) -> int:
    """Delete files and subdirectories under one profile artifact directory."""
    artifact_dir = ARTIFACTS_DIR / profile_key
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        return 0
    removed_count = 0
    for path in safe_profile_artifact_paths(artifact_dir):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed_count += 1
    return removed_count


def safe_profile_artifact_paths(artifact_dir: Path) -> list[Path]:
    """Return direct children that are safe to remove from a profile artifact directory."""
    artifacts_root = ARTIFACTS_DIR.resolve(strict=False)
    resolved_artifact_dir = artifact_dir.resolve(strict=False)
    if resolved_artifact_dir.parent != artifacts_root:
        raise ValueError(f"Refusing to clear non-profile artifact path: {artifact_dir}")
    return list(artifact_dir.iterdir())


def summary_sources(profile_key: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return the CSV and XLSX summary row sets for one profile."""
    from .streamlit_shared import summary_csv_path, summary_xlsx_path, load_csv_rows, load_xlsx_rows
    return (
        load_csv_rows(summary_csv_path(profile_key)),
        load_xlsx_rows(summary_xlsx_path(profile_key)),
    )
