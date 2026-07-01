"""Tests for manual-review correction hint import."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.core.manual_review.manual_review_hints import (
    export_manual_review_hints,
    hint_key,
    load_manual_review_hints,
)


class ManualReviewHintsTests(unittest.TestCase):
    """Validate manual-review CSV corrections become reusable hints."""

    def test_loads_only_approved_rows_with_correct_store_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "manual_review.csv"
            self._write_rows(
                source,
                [
                    self._row("1", "Panadol", "s1", "approved"),
                    self._row("2", "Wrong", "s2", "reject"),
                    self._row("3", "Blank", "", "approved"),
                ],
            )

            hints = load_manual_review_hints(source)

        self.assertEqual(list(hints), [hint_key("1", "Panadol")])
        self.assertEqual(hints[hint_key("1", "Panadol")].store_product_id, "s1")

    def test_exports_hints_to_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "manual_review.csv"
            output = Path(temp) / "hints.json"
            self._write_rows(source, [self._row("1", "Panadol", "s1", "")])

            count = export_manual_review_hints(source, output)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(count, 1)
        self.assertEqual(payload[0]["store_product_id"], "s1")

    def test_hint_key_normalizes_excel_code_and_whitespace(self) -> None:
        self.assertEqual(
            hint_key(" 001.0 ", " Panadol   Extra "),
            hint_key("001", "panadol extra"),
        )

    def test_cli_runs_as_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "manual_review.csv"
            output = Path(temp) / "hints.json"
            self._write_rows(source, [self._row("1", "Panadol", "s1", "")])

            result = subprocess.run(
                [
                    sys.executable,
                    "tools/import_manual_review_hints.py",
                    str(source),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertIn("manual_review_hints_exported:1", result.stdout)

    @staticmethod
    def _row(code: str, name: str, store_id: str, decision: str) -> dict[str, str]:
        return {
            "item_code": code,
            "item_name": name,
            "correct_store_product_id": store_id,
            "manual_decision": decision,
            "manual_reason": "",
        }

    @staticmethod
    def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
