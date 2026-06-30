"""Merge per-worker summary artifacts into the canonical profile summary."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from openpyxl import Workbook

from ...core.artifact_run import artifact_filename, current_artifact_run

_WORKER_RE = re.compile(r"(?:\.|_)worker_(\d+)(?:_|\.)")
_WORKER_PATTERNS = (
    "{label}.worker_*.csv",
    "{label}.worker_*.xlsx",
    "{label}_worker_*.csv",
    "{label}_worker_*.xlsx",
)


def merge_worker_summaries(profile_key: str, base_label: str) -> None:
    """Concatenate worker CSV/XLSX partitions into one canonical summary file."""
    artifacts_dir = _summary_dir(profile_key)
    worker_csv_files = sorted(
        _worker_csv_files(artifacts_dir, base_label), key=_worker_sort_key
    )
    if not worker_csv_files:
        return
    rows, fieldnames = _collect_worker_csv_rows(worker_csv_files)
    csv_target = _target_path(artifacts_dir, base_label, ".csv")
    xlsx_target = _target_path(artifacts_dir, base_label, ".xlsx")
    _write_merged_csv(csv_target, fieldnames, rows)
    _write_merged_xlsx(xlsx_target, fieldnames, rows)
    _remove_worker_files(artifacts_dir, base_label)


def _summary_dir(profile_key: str) -> Path:
    active = current_artifact_run()
    directory = active.directory if active else Path("artifacts") / profile_key
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _worker_csv_files(artifacts_dir: Path, base_label: str) -> list[Path]:
    patterns = (f"{base_label}.worker_*.csv", f"{base_label}_worker_*.csv")
    return [path for pattern in patterns for path in artifacts_dir.glob(pattern)]


def _target_path(artifacts_dir: Path, base_label: str, extension: str) -> Path:
    if current_artifact_run():
        return artifacts_dir / artifact_filename(base_label, extension)
    return artifacts_dir / f"{base_label}{extension}"


def _collect_worker_csv_rows(paths: list[Path]) -> tuple[list[dict], list[str]]:
    rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            current = list(reader.fieldnames or [])
            fieldnames = _merge_fieldnames(fieldnames, current, path)
            rows.extend(reader)
    return rows, fieldnames


def _merge_fieldnames(
    expected: list[str], current: list[str], path: Path
) -> list[str]:
    if not current:
        return expected
    if not expected:
        return current
    if expected != current:
        return _union_fieldnames(expected, current)
    return expected


def _union_fieldnames(expected: list[str], current: list[str]) -> list[str]:
    merged = list(expected)
    seen = set(merged)
    for field in current:
        if field not in seen:
            merged.append(field)
            seen.add(field)
    return merged


def _worker_sort_key(path: Path) -> tuple[int, str]:
    match = _WORKER_RE.search(path.name)
    return (int(match.group(1)) if match else 10**9, path.name)


def _write_merged_csv(target: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_merged_xlsx(target: Path, fieldnames: list[str], rows: list[dict]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    if worksheet is None:
        raise RuntimeError("Failed to create merged summary worksheet.")
    worksheet.append(fieldnames)
    for row in rows:
        worksheet.append([row.get(field, "") for field in fieldnames])
    workbook.save(target)


def _remove_worker_files(artifacts_dir: Path, base_label: str) -> None:
    for pattern in _WORKER_PATTERNS:
        rendered = pattern.format(label=base_label)
        for path in artifacts_dir.glob(rendered):
            try:
                path.unlink()
            except Exception:
                pass
