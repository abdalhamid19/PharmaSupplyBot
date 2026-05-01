import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.cli_commands import load_order_items, resumable_order_items
from src.excel import Item


class CliCommandsTests(unittest.TestCase):
    def test_resumable_order_items_skips_items_already_in_summary(self) -> None:
        items = [
            Item(code="1", name="Panadol", qty=1),
            Item(code="", name="Devarol", qty=2),
        ]
        args = SimpleNamespace(resume=True)

        with TemporaryDirectory() as temp_dir:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp_dir)
                summary_dir = Path("artifacts") / "wardany"
                summary_dir.mkdir(parents=True)
                (summary_dir / "order_result_summary.csv").write_text(
                    "item_code,item_name,status\n1,Panadol,added-to-cart\n",
                    encoding="utf-8",
                )

                remaining = resumable_order_items("wardany", items, args)
            finally:
                os.chdir(original_cwd)

        self.assertEqual(remaining, [items[1]])

    def test_load_order_items_filters_prevented_items(self) -> None:
        items = [
            Item(code="1", name="Blocked", qty=1),
            Item(code="2", name="Allowed", qty=1),
        ]
        args = SimpleNamespace(
            excel="input/orders.xlsx",
            limit=0,
            prevented_items_excel="input/drugprevented.xlsx",
        )

        with (
            patch("src.cli_commands.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=True),
            patch(
                "src.cli_commands.load_prevented_items",
                return_value=[SimpleNamespace(code="1", name="Blocked")],
            ),
        ):
            allowed_items = load_order_items(SimpleNamespace(excel=SimpleNamespace()), args)

        self.assertEqual(allowed_items, [items[1]])

    def test_load_order_items_ignores_missing_prevented_items_file(self) -> None:
        items = [Item(code="1", name="Allowed", qty=1)]
        args = SimpleNamespace(
            excel="input/orders.xlsx",
            limit=0,
            prevented_items_excel="input/missing.xlsx",
        )

        with (
            patch("src.cli_commands.load_items_from_excel", return_value=items),
            patch("pathlib.Path.is_file", return_value=False),
        ):
            allowed_items = load_order_items(SimpleNamespace(excel=SimpleNamespace()), args)

        self.assertEqual(allowed_items, items)


if __name__ == "__main__":
    unittest.main()
