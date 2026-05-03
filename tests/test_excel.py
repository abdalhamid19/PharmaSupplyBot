from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.config_models import ExcelConfig
from src.excel import load_items_from_excel


class ExcelTests(unittest.TestCase):
    def test_load_items_reads_report_with_title_row(self) -> None:
        config = ExcelConfig(code_col="كود", name_col="إسم الصنف", qty_col="كمية النقص")
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.xlsx"
            pd.DataFrame(
                [
                    ["مبيعات الأصناف فى جميع المخازن", None, None],
                    ["كود", "إسم الصنف", "كمية النقص"],
                    [73368, "KENACOMB CREAM 15 GM", 2],
                ]
            ).to_excel(path, index=False, header=False)

            items = load_items_from_excel(path, config)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].code, "73368")
        self.assertEqual(items[0].name, "KENACOMB CREAM 15 GM")
        self.assertEqual(items[0].qty, 2)

    def test_load_items_keeps_normal_header_row_support(self) -> None:
        config = ExcelConfig(code_col="code", name_col="name", qty_col="qty")
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.xlsx"
            pd.DataFrame(
                [{"code": 123, "name": "ASPIRIN", "qty": 3}]
            ).to_excel(path, index=False)

            items = load_items_from_excel(path, config)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].code, "123")
        self.assertEqual(items[0].name, "ASPIRIN")
        self.assertEqual(items[0].qty, 3)


if __name__ == "__main__":
    unittest.main()
