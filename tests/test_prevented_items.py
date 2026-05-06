import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.core.prevented_items import (
    PREVENTED_CODE_COLUMN,
    PREVENTED_NAME_COLUMN,
    PreventedItem,
    add_prevented_item,
    filter_prevented_order_items,
    load_prevented_items,
    remove_prevented_item,
    save_prevented_items,
)
from src.core.utils.excel import Item


class PreventedItemsTests(unittest.TestCase):
    def test_load_prevented_items_reads_expected_columns(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "prevented.xlsx"
            pd.DataFrame(
                [
                    {PREVENTED_CODE_COLUMN: 47273, PREVENTED_NAME_COLUMN: "DEVAROL"},
                    {PREVENTED_CODE_COLUMN: "", PREVENTED_NAME_COLUMN: "L-CARNITINE"},
                ]
            ).to_excel(path, index=False)

            prevented_items = load_prevented_items(path)

        self.assertEqual(
            prevented_items,
            [
                PreventedItem(code="47273", name="DEVAROL"),
                PreventedItem(code="", name="L-CARNITINE"),
            ],
        )

    def test_filter_prevented_order_items_blocks_matching_name_only(self) -> None:
        items = [
            Item(code="47273", name="DEVAROL", qty=1),
            Item(code="47273", name="IVERZINE LOTION 6O ML", qty=1),
            Item(code="1", name="Allowed", qty=2),
        ]
        prevented_items = [PreventedItem(code="47273", name="DEVAROL")]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        self.assertEqual(allowed_items, [items[1], items[2]])

    def test_filter_prevented_order_items_blocks_code_only_entries(self) -> None:
        items = [
            Item(code="47273", name="IVERZINE LOTION 6O ML", qty=1),
            Item(code="1", name="Allowed", qty=2),
        ]
        prevented_items = [PreventedItem(code="47273", name="")]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        self.assertEqual(allowed_items, [items[1]])

    def test_filter_prevented_order_items_blocks_matching_name_regardless_code(
        self,
    ) -> None:
        items = [
            Item(code="", name="  Devarol   S  ", qty=1),
            Item(code="1", name="Devarol S", qty=2),
            Item(code="", name="Allowed", qty=3),
        ]
        prevented_items = [PreventedItem(code="999", name="Devarol S")]

        allowed_items = list(filter_prevented_order_items(items, prevented_items))

        self.assertEqual(allowed_items, [items[2]])

    def test_add_remove_and_save_prevented_items(self) -> None:
        prevented_items = [PreventedItem(code="1", name="Panadol")]
        updated_items = add_prevented_item(prevented_items, "2", "Devarol")
        updated_items = remove_prevented_item(updated_items, "1", "Panadol")

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "prevented.xlsx"
            save_prevented_items(updated_items, path)
            reloaded_items = load_prevented_items(path)

        self.assertEqual(reloaded_items, [PreventedItem(code="2", name="Devarol")])


if __name__ == "__main__":
    unittest.main()
