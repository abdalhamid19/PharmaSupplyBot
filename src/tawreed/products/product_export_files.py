"""Tawreed product export file I/O helpers."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

from .product_export_rows import EXPORT_FIELDNAMES, ProductExportRow

# Constants
SUPPORTED_EXPORT_FORMATS = ("csv", "xlsx", "txt")
DEFAULT_EXPORT_STEM = "tawreed_products"


def write_product_export_files(
    rows: Iterable[ProductExportRow], output_dir: Path, stem: str
) -> dict[str, Path]:
    """Write Tawreed product export rows to CSV, XLSX, and tab-delimited TXT."""
    materialized_rows = list(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": _write_csv(materialized_rows, output_dir / f"{stem}.csv"),
        "xlsx": _write_xlsx(materialized_rows, output_dir / f"{stem}.xlsx"),
        "txt": _write_txt(materialized_rows, output_dir / f"{stem}.txt"),
    }


def _write_csv(rows: list[ProductExportRow], path: Path) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(EXPORT_FIELDNAMES)
        writer.writerows(row.values() for row in rows)
    return path


def _write_xlsx(rows: list[ProductExportRow], path: Path) -> Path:
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("tawreed_products")
    worksheet.append(list(EXPORT_FIELDNAMES))
    for row in rows:
        worksheet.append(row.values())
    workbook.save(path)
    return path


def _write_txt(rows: list[ProductExportRow], path: Path) -> Path:
    with path.open("w", encoding="utf-8", newline="") as output_file:
        output_file.write("\t".join(EXPORT_FIELDNAMES) + "\n")
        for row in rows:
            output_file.write("\t".join(row.values()) + "\n")
    return path


__all__ = [
    "SUPPORTED_EXPORT_FORMATS",
    "DEFAULT_EXPORT_STEM",
    "write_product_export_files",
]
