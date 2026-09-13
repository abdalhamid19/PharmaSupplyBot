from src.tawreed.matching.tawreed_strategy import (
    choose_store_index,
    preferred_warehouse_row_index,
)
from src.tawreed.order.tawreed_order_processing import OrderItemProcessor
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest


def test_choose_store_index_uses_lowest_purchase_price():
    stores = [
        {"availableQuantity": 2, "discountPercent": "10%", "salePrice": 9},
        {"availableQuantity": 5, "discountPercent": "5%", "salePrice": 8},
        {"availableQuantity": 3, "discountPercent": "0.15", "salePrice": 7},
    ]

    assert choose_store_index(stores, "lowest_purchase_price", RuntimeError) == 2


def test_choose_store_index_applies_preference_on_exact_price_tie():
    stores = [
        {"storeName": "عنايه", "availableQuantity": 54, "discountPercent": 35, "salePrice": 8},
        {"storeName": "الفا فارما", "availableQuantity": 53, "discountPercent": 10, "salePrice": 8},
    ]

    assert choose_store_index(
        stores, "lowest_purchase_price", RuntimeError, ["شركه الفا فارما (الجيزه)"]
    ) == 1


def test_choose_store_index_uses_cheapest_price_before_configured_priority():
    stores = [
        {
            "storeName": "شركه البركه (الجيزه)",
            "availableQuantity": 18,
            "salePrice": 18.40,
        },
        {
            "storeName": "شركة الفا فارما (الجيزه)",
            "availableQuantity": 53,
            "salePrice": 18.20,
        },
    ]

    assert choose_store_index(
        stores,
        "lowest_purchase_price",
        RuntimeError,
        ["شركه البركه (الجيزه)", "شركه الفا فارما (الجيزه)"],
    ) == 1


class _QuantityLocator:
    def __init__(self, value: int):
        self.value = value

    @property
    def first(self):
        return self

    def inner_text(self, timeout=None):
        return str(self.value)


class _WarehouseRow:
    def __init__(self, name: str, quantity: int):
        self.name = name
        self.quantity = quantity

    def inner_text(self, timeout=None):
        return self.name

    def locator(self, _selector):
        return _QuantityLocator(self.quantity)


class _WarehouseRows:
    def __init__(self, rows):
        self.rows = rows

    def count(self):
        return len(self.rows)

    def nth(self, index):
        return self.rows[index]


def test_legacy_rows_apply_preference_before_displayed_order_or_quantity():
    rows = _WarehouseRows(
        [
            _WarehouseRow("شركه عنايه للادويه 35%", 54),
            _WarehouseRow("شركة الفا فارما (الجيزه) 10%", 53),
        ]
    )

    preferred = ["شركه الفا فارما (الجيزه)"]
    assert preferred_warehouse_row_index(rows, preferred) == 1


def test_legacy_row_selection_skips_out_of_stock_preferred_row():
    rows = _WarehouseRows(
        [_WarehouseRow("شركه الفا فارما (الجيزه)", 0), _WarehouseRow("عنايه", 54)]
    )

    assert preferred_warehouse_row_index(rows, ["شركه الفا فارما (الجيزه)"], ".available") == 1


def test_legacy_row_selection_returns_no_candidate_when_all_rows_are_out_of_stock():
    rows = _WarehouseRows(
        [_WarehouseRow("شركه الفا فارما (الجيزه)", 0), _WarehouseRow("عنايه", 0)]
    )
    preferred = ["شركه الفا فارما (الجيزه)"]

    assert preferred_warehouse_row_index(rows, preferred, ".available") is None


def test_legacy_row_chooser_applies_discount_floor_before_warehouse_preference():
    rows = _WarehouseRows(
        [
            _WarehouseRow("Ø´Ø±ÙƒØ© Ø§Ù„ÙØ§ ÙØ§Ø±Ù…Ø§ 8%", 53),
            _WarehouseRow("Ø´Ø±ÙƒÙ‡ Ø¹Ù†Ø§ÙŠÙ‡ 35%", 54),
        ]
    )
    preferred = ["Ø´Ø±ÙƒØ© Ø§Ù„ÙØ§ ÙØ§Ø±Ù…Ø§"]

    assert preferred_warehouse_row_index(
        rows, preferred, ".available", min_discount_percent=10
    ) == 1


def test_legacy_row_chooser_returns_none_when_all_discounts_are_below_floor():
    rows = _WarehouseRows(
        [_WarehouseRow("Ø´Ø±ÙƒØ© Ø§Ù„ÙØ§ ÙØ§Ø±Ù…Ø§ 8%", 53)]
    )

    assert preferred_warehouse_row_index(
        rows, [], ".available", min_discount_percent=10
    ) is None


def test_legacy_processor_rejects_unpriced_warehouse_rows():
    rows = Mock()
    rows.count.return_value = 1
    bot = SimpleNamespace(
        config=SimpleNamespace(
            warehouse_strategy={"mode": "lowest_purchase_price"},
        ),
        selectors=SimpleNamespace(warehouse_rows=".warehouse"),
        skip_item_exception=RuntimeError,
    )
    processor = OrderItemProcessor(bot)
    page = Mock()
    page.locator.return_value = rows

    with pytest.raises(RuntimeError, match="structured purchase price"):
        processor.pick_warehouse_if_needed(page)
