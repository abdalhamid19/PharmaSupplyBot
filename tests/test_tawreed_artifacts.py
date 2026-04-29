import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import Workbook, load_workbook

from src.tawreed_artifacts import append_xlsx_artifact


class TawreedArtifactsTests(unittest.TestCase):
    def test_append_xlsx_artifact_rewrites_changed_headers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                artifact_dir = Path("artifacts") / "wardany"
                artifact_dir.mkdir(parents=True)
                artifact_path = artifact_dir / "order_result_summary.xlsx"
                workbook = Workbook()
                worksheet = workbook.active
                worksheet.append(["item_code", "matched_query", "searched_queries_count"])
                worksheet.append(["123", "Panadol", 2])
                workbook.save(artifact_path)

                append_xlsx_artifact(
                    "wardany",
                    "order_result_summary",
                    [
                        {
                            "item_code": "456",
                            "matched_query": "Panadol Advance",
                            "selected_discount_percent": "35%",
                            "selected_store_name": "Abu Amira",
                            "searched_queries_count": 3,
                        }
                    ],
                )

                loaded = load_workbook(artifact_path)
                values = list(loaded.active.iter_rows(values_only=True))
            finally:
                os.chdir(original_cwd)

        self.assertEqual(
            values[0],
            (
                "item_code",
                "matched_query",
                "selected_discount_percent",
                "selected_store_name",
                "searched_queries_count",
            ),
        )
        self.assertEqual(values[1], ("123", "Panadol", None, None, 2))
        self.assertEqual(values[2], ("456", "Panadol Advance", "35%", "Abu Amira", 3))


if __name__ == "__main__":
    unittest.main()
