import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from src.cli_commands import resumable_order_items
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


if __name__ == "__main__":
    unittest.main()
