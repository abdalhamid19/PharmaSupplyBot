"""Tests for Tawreed product catalog export helpers."""

from __future__ import annotations

import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from openpyxl import load_workbook

from src.tawreed.tawreed_product_export_api import iter_all_product_candidates
from src.tawreed.tawreed_product_export_files import write_product_export_files
from src.tawreed.tawreed_product_export_rows import (
    EXPORT_FIELDNAMES,
    ProductExportRow,
    product_export_rows,
)


class TawreedProductExportTests(unittest.TestCase):
    """Validate Tawreed product export normalization, pagination, and files."""

    def test_product_export_rows_normalize_and_deduplicate_candidates(self) -> None:
        candidates = [
            {
                "productName": "  بانادول  ",
                "productNameEn": " Panadol ",
                "storeProductId": 123,
            },
            {
                "productName": "بانادول",
                "productNameEn": "Panadol",
                "storeProductId": 123,
            },
            {},
        ]

        rows = list(product_export_rows(candidates))

        self.assertEqual(rows, [ProductExportRow("بانادول", "Panadol", "123")])

    def test_write_product_export_files_creates_all_requested_formats(self) -> None:
        rows = [ProductExportRow("بانادول", "Panadol", "123")]

        with TemporaryDirectory() as temp_dir:
            paths = write_product_export_files(rows, Path(temp_dir), "catalog")
            csv_rows = _read_csv_rows(paths["csv"])
            txt_lines = paths["txt"].read_text(encoding="utf-8").splitlines()
            xlsx_header = _read_xlsx_header(paths["xlsx"])

        self.assertEqual(set(paths.keys()), {"csv", "xlsx", "txt"})
        self.assertEqual(csv_rows[0], list(EXPORT_FIELDNAMES))
        self.assertIn("بانادول\tPanadol\t123", txt_lines)
        self.assertEqual(xlsx_header, EXPORT_FIELDNAMES)

    def test_iter_all_product_candidates_pages_until_total_pages(self) -> None:
        page = _FakePage([_payload(2, "1"), _payload(2, "2")])

        candidates = list(iter_all_product_candidates(page, page_size=10))

        self.assertEqual([row["storeProductId"] for row in candidates], ["1", "2"])
        self.assertEqual(page.request.urls[0].split("page=")[1].split("&")[0], "0")
        self.assertEqual(page.request.urls[1].split("page=")[1].split("&")[0], "1")

    def test_iter_all_product_candidates_honors_limit(self) -> None:
        page = _FakePage([_payload(3, "1", "2")])

        candidates = list(iter_all_product_candidates(page, page_size=10, limit=1))

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["storeProductId"], "1")


def _read_csv_rows(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as input_file:
        return list(csv.reader(input_file))


def _read_xlsx_header(path: Path) -> tuple[str, ...]:
    workbook = load_workbook(path, read_only=True)
    try:
        return next(workbook.active.iter_rows(values_only=True))
    finally:
        workbook.close()


def _payload(total_pages: int, *store_product_ids: str) -> dict[str, Any]:
    return {
        "data": {
            "totalPages": total_pages,
            "content": [
                {
                    "productName": "عربي",
                    "productNameEn": "English",
                    "storeProductId": value,
                }
                for value in store_product_ids
            ],
        }
    }


class _FakePage:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.request = _FakeRequest(payloads)

    def evaluate(self, expression: str) -> str:
        return "https://seller.tawreed.io"


class _FakeRequest:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.urls: list[str] = []

    def post(self, url: str, data: Any, headers: dict[str, str]) -> "_FakeResponse":
        self.urls.append(url)
        return _FakeResponse(self.payloads.pop(0))


class _FakeResponse:
    ok = True
    status = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload


if __name__ == "__main__":
    unittest.main()
