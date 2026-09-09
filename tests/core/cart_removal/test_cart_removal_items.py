import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from src.core.cart.cart_removal_items import (
    REMOVE_CODE_COLUMN,
    REMOVE_NAME_COLUMN,
    CartRemovalItem,
    cart_row_matches_item,
    load_cart_removal_items,
)
from src.cli.commands.cli_cart_removal_source import cart_removal_items
from src.core.utils.excel import Item


class CartRemovalItemsTests(unittest.TestCase):
    def test_load_cart_removal_items_reads_expected_columns_and_normalizes_code(
        self,
    ) -> None:
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

            items = list(load_cart_removal_items(path))

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

    def test_load_cart_removal_items_accepts_order_sheet_code_header(self) -> None:
        """The order sheet's ``الكود`` header is valid for cart removal too."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "order-items.xlsx"
            pd.DataFrame(
                [{"الكود": 47273, "إسم الصنف": "DEVAROL", "الكمية المطلوبة": 2}]
            ).to_excel(path, index=False)

            items = list(load_cart_removal_items(path))

        self.assertEqual(
            items,
            [CartRemovalItem(code="47273", name="DEVAROL")],
        )

    def test_cart_removal_items_limits_loaded_sheet(self) -> None:
        """The CLI limit keeps only the first N parsed removal items."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "large-remove.xlsx"
            pd.DataFrame(
                [
                    {"الكود": 1, "إسم الصنف": "ONE"},
                    {"الكود": 2, "إسم الصنف": "TWO"},
                    {"الكود": 3, "إسم الصنف": "THREE"},
                ]
            ).to_excel(path, index=False)

            items = cart_removal_items(
                Namespace(
                    excel=str(path),
                    limit=2,
                    from_manual_review=None,
                    manual_review_scope="current-run",
                ),
                load_cart_removal_items,
            )

        self.assertEqual(
            items,
            [
                CartRemovalItem(code="1", name="ONE"),
                CartRemovalItem(code="2", name="TWO"),
            ],
        )

    def test_order_sheet_uses_order_loader_before_limit(self) -> None:
        """Removal follows order filtering/order before applying ``--limit``."""
        args = Namespace(
            excel="order.xlsx",
            limit=2,
            from_manual_review=None,
            manual_review_scope="current-run",
        )
        order_items = [
            Item(code="2", name="SECOND", qty=1),
            Item(code="1", name="FIRST", qty=1),
            Item(code="3", name="THIRD", qty=1),
        ]

        with patch(
            "src.cli.commands.cli_cart_removal_source.load_regular_order_items",
            return_value=order_items,
        ):
            items = cart_removal_items(args, load_cart_removal_items, object())

        self.assertEqual(
            items,
            [
                CartRemovalItem(code="2", name="SECOND"),
                CartRemovalItem(code="1", name="FIRST"),
            ],
        )

    def test_legacy_remove_sheet_falls_back_when_quantity_is_missing(self) -> None:
        """Two-column remove sheets retain their legacy parsing behavior."""
        app_config = type(
            "Config",
            (),
            {"excel": type("Excel", (), {"qty_col": "quantity"})()},
        )()
        args = Namespace(
            excel="remove.xlsx",
            limit=0,
            from_manual_review=None,
            manual_review_scope="current-run",
        )
        with (
            patch(
                "src.cli.commands.cli_cart_removal_source.load_regular_order_items",
                side_effect=ValueError(
                    "Missing required Excel columns: ['quantity']."
                ),
            ),
        ):
            items = cart_removal_items(
                args,
                lambda _path: [CartRemovalItem(code="1", name="ONE")],
                app_config,
            )

        self.assertEqual(items, [CartRemovalItem(code="1", name="ONE")])


if __name__ == "__main__":
    unittest.main()
