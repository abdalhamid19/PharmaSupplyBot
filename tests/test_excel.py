from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from src.core.config.config_models import ExcelConfig
from src.core.utils.excel import load_items_from_excel


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

    def test_load_items_raises_clear_error_for_missing_columns(self) -> None:
        config = ExcelConfig(code_col="code", name_col="name", qty_col="qty")
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.xlsx"
            pd.DataFrame([{"code": 123, "name": "ASPIRIN"}]).to_excel(path, index=False)

            with self.assertRaises(KeyError) as context:
                load_items_from_excel(path, config)

        self.assertIn("Missing one or more required Excel columns", str(context.exception))
        self.assertIn("qty", str(context.exception))

    def test_load_items_coerces_and_limits_quantities_in_single_pass(self) -> None:
        config = ExcelConfig(code_col="code", name_col="name", qty_col="qty", min_qty=1, max_qty=4)
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "orders.xlsx"
            pd.DataFrame(
                [
                    {"code": 123, "name": "ASPIRIN", "qty": "2.6"},
                    {"code": 124, "name": "VITAMIN C", "qty": "10"},
                    {"code": 125, "name": "IGNORE", "qty": ""},
                ]
            ).to_excel(path, index=False)

            items = load_items_from_excel(path, config)

        self.assertEqual([(item.code, item.qty) for item in items], [("123", 3), ("124", 4)])


if __name__ == "__main__":
    unittest.main()
