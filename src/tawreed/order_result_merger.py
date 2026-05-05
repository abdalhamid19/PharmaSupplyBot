"""Merge per-worker summary artifacts into the canonical profile summary."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook


def merge_worker_summaries(profile_key: str, base_label: str) -> None:
    """Concatenate worker CSV/XLSX partitions into one canonical summary file."""
    artifacts_dir = Path("artifacts") / profile_key
    worker_csv_files = sorted(artifacts_dir.glob(f"{base_label}.worker_*.csv"))
    if not worker_csv_files:
        return
    rows, fieldnames = _collect_worker_csv_rows(worker_csv_files)
    _write_merged_csv(artifacts_dir / f"{base_label}.csv", fieldnames, rows)
    _write_merged_xlsx(artifacts_dir / f"{base_label}.xlsx", fieldnames, rows)
    _remove_worker_files(artifacts_dir, base_label)


def _collect_worker_csv_rows(paths: list[Path]) -> tuple[list[dict], list[str]]:
    """Read all worker CSV files and return rows with the canonical fieldnames."""
    rows: list[dict[str, str]] = []
    fieldnames: list[str] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not fieldnames and reader.fieldnames:
                fieldnames = list(reader.fieldnames)
            rows.extend(reader)
    return rows, fieldnames


def _write_merged_csv(target: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write the merged rows into the canonical CSV summary."""
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_merged_xlsx(target: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Write the merged rows into the canonical XLSX summary."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(fieldnames)
    for row in rows:
        worksheet.append([row.get(field, "") for field in fieldnames])
    workbook.save(target)


def _remove_worker_files(artifacts_dir: Path, base_label: str) -> None:
    """Delete per-worker CSV and XLSX partition files after successful merge."""
    for pattern in (f"{base_label}.worker_*.csv", f"{base_label}.worker_*.xlsx"):
        for path in artifacts_dir.glob(pattern):
            try:
                path.unlink()
            except Exception:
                pass
