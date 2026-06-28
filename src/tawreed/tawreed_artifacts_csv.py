"""CSV artifact helpers for Tawreed."""

from __future__ import annotations

import csv
from pathlib import Path


def _ensure_csv_schema(artifact_path: Path, fieldnames: list[str]) -> None:
    """Rewrite an existing CSV artifact when its schema has changed."""
    if not artifact_path.exists():
        return
    existing_fieldnames = _csv_header_fieldnames(artifact_path)
    if existing_fieldnames and existing_fieldnames != fieldnames:
        _rewrite_csv_artifact_with_fieldnames(artifact_path, fieldnames)


def _csv_artifact_fieldnames(
    artifact_path: Path, rows: list[dict[str, object]]
) -> list[str]:
    """Return existing CSV columns plus any new row keys in first-seen order."""
    fieldnames = _csv_header_fieldnames(artifact_path) if artifact_path.exists() else []
    return _merge_row_fieldnames(fieldnames, rows)


def _append_csv_rows(
    artifact_path: Path, fieldnames: list[str], rows: list[dict[str, object]]
) -> None:
    """Append rows to a CSV artifact with a header when needed."""
    write_header = not artifact_path.exists() or artifact_path.stat().st_size == 0
    with artifact_path.open("a", encoding="utf-8", newline="") as artifact_file:
        writer = csv.DictWriter(artifact_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def _csv_header_fieldnames(artifact_path: Path) -> list[str]:
    """Return the existing CSV header row fieldnames when the file is present."""
    with artifact_path.open("r", encoding="utf-8", newline="") as artifact_file:
        reader = csv.DictReader(artifact_file)
        return list(reader.fieldnames or [])


def _rewrite_csv_artifact_with_fieldnames(
    artifact_path: Path, fieldnames: list[str]
) -> None:
    """Rewrite an existing CSV artifact so all rows conform to the requested fieldnames."""
    with artifact_path.open("r", encoding="utf-8", newline="") as artifact_file:
        reader = csv.DictReader(artifact_file)
        existing_rows = list(reader)
    with artifact_path.open("w", encoding="utf-8", newline="") as artifact_file:
        writer = csv.DictWriter(artifact_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing_rows:
            writer.writerow(
                {field_name: row.get(field_name, "") for field_name in fieldnames}
            )


def _merge_row_fieldnames(
    fieldnames: list[str], rows: list[dict[str, object]]
) -> list[str]:
    """Return fieldnames extended with keys that appear in the supplied rows."""
    merged = list(fieldnames)
    seen = set(merged)
    for row in rows:
        for key in row:
            if key not in seen:
                merged.append(key)
                seen.add(key)
    return merged
