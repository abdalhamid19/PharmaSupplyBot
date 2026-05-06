"""Tests for the current Tawreed products-page add-to-cart flow."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from src.core.matching_models import SearchMatch
from src.core.utils.excel import Item
from src.tawreed.tawreed_products_flow import (
    add_item_from_store_dialogs,
    open_add_to_cart_for_match,
)


class _FakeButton:
    """Minimal clickable button test double."""

    def __init__(self) -> None:
        self.click_count = 0

    def click(self) -> None:
        self.click_count += 1

    def is_enabled(self) -> bool:
        return True


class _FakeCartButtons:
    """Record which store-dialog cart buttons were clicked."""

    def __init__(self) -> None:
        self.clicked_indices: list[int] = []

    def nth(self, index: int) -> _FakeButton:
        self.clicked_indices.append(index)
        return _FakeButton()


class TawreedProductsFlowTests(unittest.TestCase):
    """Focused regression tests for selected store summary values."""

    def test_direct_dom_match_records_discount_and_store_name(self) -> None:
        """Direct cart adds populate selected-store columns before summarizing."""
        bot = _bot(warehouse_mode="first_available")
        match = SearchMatch(
            query="E MOX 500 MG CAP",
            row_index=0,
            score=18.0,
            data={
                "productsCount": 25,
                "availableQuantity": 25,
                "discountPercent": "40.5",
                "supplierName": "شركه ابو عميره (الجيزه)",
                "storeProductId": "dom-row-emox",
            },
        )

        page: Any = object()
        row: Any = object()
        with (
            patch(
                "src.tawreed.tawreed_products_flow.cart_button",
                return_value=_FakeButton(),
            ),
            patch("src.tawreed.tawreed_products_flow.wait_for_row_to_settle"),
            patch(
                "src.tawreed.tawreed_products_flow.fill_add_to_cart_dialog",
                return_value=3,
            ),
        ):
            open_add_to_cart_for_match(bot, page, row, Item("1", "E MOX", 3), match)

        self.assertEqual(bot.last_ordered_total_qty, 3)
        self.assertEqual(bot.last_selected_discount_percent, "40.5%")
        self.assertEqual(bot.last_selected_store_name, "شركه ابو عميره (الجيزه)")

    def test_multi_store_add_records_split_discount_and_store_name(self) -> None:
        """Multi-store adds retain every selected store in summary columns."""
        bot = _bot(warehouse_mode="first_available")
        requested_quantities: list[int] = []
        clicked = _FakeCartButtons()
        page: Any = object()
        row: Any = object()

        with _patched_multi_store_flow(
            bot,
            clicked,
            _split_store_rows(),
            requested_quantities,
        ):
            add_item_from_store_dialogs(bot, page, row, Item("1", "DEVAROL", 7))

        self.assertEqual(clicked.clicked_indices, [0, 1])
        self.assertEqual(requested_quantities, [2, 5])
        self.assertEqual(bot.last_ordered_total_qty, 7)
        self.assertEqual(
            bot.last_selected_discount_percent, "20% (qty 2) | 30% (qty 5)"
        )
        self.assertEqual(
            bot.last_selected_store_name, "First Store (qty 2) | Second Store (qty 5)"
        )

    def test_max_discount_add_records_best_store_metadata(self) -> None:
        """Highest-discount mode records the selected best-discount store."""
        bot = _bot(warehouse_mode="max_discount")
        requested_quantities: list[int] = []
        clicked = _FakeCartButtons()
        page: Any = object()
        row: Any = object()

        with _patched_multi_store_flow(
            bot,
            clicked,
            _split_store_rows(),
            requested_quantities,
        ):
            add_item_from_store_dialogs(bot, page, row, Item("1", "DEVAROL", 7))

        self.assertEqual(clicked.clicked_indices, [1])
        self.assertEqual(requested_quantities, [5])
        self.assertEqual(bot.last_ordered_total_qty, 5)
        self.assertEqual(bot.last_selected_discount_percent, "30% (qty 5)")
        self.assertEqual(bot.last_selected_store_name, "Second Store (qty 5)")


def _bot(warehouse_mode: str) -> SimpleNamespace:
    """Return a minimal bot-like object for products-flow tests."""
    return SimpleNamespace(
        config=SimpleNamespace(
            runtime=SimpleNamespace(timeout_ms=5000),
            warehouse_strategy={"mode": warehouse_mode},
        ),
        skip_item_exception=RuntimeError,
        last_selected_discount_percent="",
        last_selected_store_name="",
        last_ordered_total_qty=0,
    )


def _split_store_rows() -> list[dict[str, object]]:
    """Return store rows used by split and max-discount tests."""
    return [
        {
            "availableQuantity": 2,
            "storeProductId": "store-1",
            "storeName": "First Store",
            "discountPercent": 20,
        },
        {
            "availableQuantity": 5,
            "storeProductId": "store-2",
            "storeName": "Second Store",
            "discountPercent": 30,
        },
    ]


def _patched_multi_store_flow(bot, clicked, store_rows, requested_quantities):
    """Patch Playwright interactions while preserving selection logic."""

    def remember_quantity(_bot, _page, quantity: int) -> int:
        requested_quantities.append(quantity)
        return quantity

    return patch.multiple(
        "src.tawreed.tawreed_products_flow",
        open_stores_dialog=Mock(side_effect=[store_rows, store_rows]),
        visible_dialog=Mock(return_value=object()),
        store_dialog_cart_buttons=Mock(return_value=clicked),
        fill_add_to_cart_dialog=Mock(side_effect=remember_quantity),
    )


if __name__ == "__main__":
    unittest.main()
