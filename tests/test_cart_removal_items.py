import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.cart_removal_items import (
    REMOVE_CODE_COLUMN,
    REMOVE_NAME_COLUMN,
    CartRemovalItem,
    cart_row_matches_item,
    load_cart_removal_items,
)


class CartRemovalItemsTests(unittest.TestCase):
    def test_load_cart_removal_items_reads_expected_columns_and_normalizes_code(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "remove.xlsx"
            pd.DataFrame(
                [
                    {REMOVE_CODE_COLUMN: 47273, REMOVE_NAME_COLUMN: "DEVAROL"},
                    {REMOVE_CODE_COLUMN: "", REMOVE_NAME_COLUMN: "MOBIC"},
                    {REMOVE_CODE_COLUMN: 111, REMOVE_NAME_COLUMN: ""},
                    {REMOVE_CODE_COLUMN: "", REMOVE_NAME_COLUMN: ""},
                ]
            ).to_excel(path, index=False)

            items = load_cart_removal_items(path)

        self.assertEqual(
            items,
            [
                CartRemovalItem(code="47273", name="DEVAROL"),
                CartRemovalItem(code="", name="MOBIC"),
            ],
        )

    def test_cart_row_matches_by_name_only(self) -> None:
        self.assertFalse(
            cart_row_matches_item(
                "supplier row 47273 something",
                CartRemovalItem(code="47273", name="Different"),
            )
        )
        self.assertTrue(
            cart_row_matches_item(
                "supplier row mobic 15mg 30 tab",
                CartRemovalItem(code="73879", name="MOBIC 15MG 30 TAB"),
            )
        )
        self.assertFalse(
            cart_row_matches_item(
                "supplier row panadol",
                CartRemovalItem(code="47273", name="DEVAROL"),
            )
        )


if __name__ == "__main__":
    unittest.main()
