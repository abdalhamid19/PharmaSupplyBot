"""Regression tests for browser-side Excel Target cart gating."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from src.core.matching_types import SearchMatch
from src.core.ordering.excel_target_cart_gate import CartGateDecision
from src.core.utils.excel import Item
from src.tawreed.order.tawreed_order_processing import OrderItemProcessor
from src.tawreed.products.tawreed_products_flow import (
    add_item_from_store_dialogs,
    open_add_to_cart_for_match,
)


ITEM = Item(code="12345", name="CAL MAG", qty=3)


def _bot() -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            runtime=SimpleNamespace(timeout_ms=5000),
            warehouse_strategy={"mode": "lowest_purchase_price"},
            excel_target_cart_gate_run_key="wardany/run-1",
            database=SimpleNamespace(order_runs_enabled=True, order_runs_path=""),
        ),
        skip_item_exception=RuntimeError,
        last_ordered_total_qty=0,
        match_only=False,
    )


def _match() -> SearchMatch:
    return SearchMatch(
        query=ITEM.name,
        row_index=0,
        score=100.0,
        data={
            "productsCount": 0,
            "storeProductId": "tawreed-1",
            "retailPrice": 100.0,
            "salePrice": 100.0,
        },
    )


def test_single_store_does_not_open_cart_when_excel_target_is_cheaper() -> None:
    bot = _bot()
    decision = CartGateDecision(
        True,
        90.0,
        "Excel Target purchase price 90.00 is lower than or within 0.25 EGP of Tawreed purchase price 100.00",
    )

    with (
        patch(
            "src.tawreed.products.tawreed_products_flow.ExcelTargetCartGate.evaluate",
            return_value=decision,
        ),
        patch("src.tawreed.products.tawreed_products_flow._click_cart") as click_cart,
        patch(
            "src.tawreed.products.tawreed_products_flow.fill_add_to_cart_dialog",
            return_value=ITEM.qty,
        ),
        patch(
            "src.tawreed.products.tawreed_products_flow._record_single_store_selection"
        ),
    ):
        with pytest.raises(RuntimeError, match="deferred_to_excel_target"):
            open_add_to_cart_for_match(bot, Mock(), Mock(), ITEM, _match())

    click_cart.assert_not_called()


def test_multi_store_preflights_all_selected_stores_before_first_quantity_dialog() -> None:
    bot = _bot()
    page = Mock()
    rows = [
        {
            "availableQuantity": 2,
            "storeProductId": "store-1",
            "retailPrice": 100.0,
            "salePrice": 100.0,
        },
        {
            "availableQuantity": 5,
            "storeProductId": "store-2",
            "retailPrice": 100.0,
            "salePrice": 100.0,
        },
    ]
    decision = CartGateDecision(
        True,
        90.0,
        "Excel Target purchase price 90.00 is lower than or within 0.25 EGP of Tawreed purchase price 100.00",
    )
    cart_buttons = Mock()
    cart_buttons.nth.return_value = Mock()

    with (
        patch(
            "src.tawreed.products.tawreed_products_flow.open_stores_dialog",
            return_value=rows,
        ),
        patch(
            "src.tawreed.products.tawreed_products_flow.ExcelTargetCartGate.evaluate_candidates",
            return_value=decision,
        ),
        patch(
            "src.tawreed.products.tawreed_products_flow.store_dialog_cart_buttons",
            return_value=cart_buttons,
        ),
        patch("src.tawreed.products.tawreed_products_flow.visible_dialog"),
        patch("src.tawreed.products.tawreed_products_flow.fill_add_to_cart_dialog") as fill,
    ):
        with pytest.raises(RuntimeError, match="Excel Target"):
            add_item_from_store_dialogs(bot, page, Mock(), ITEM)

    cart_buttons.nth.assert_not_called()
    fill.assert_not_called()


def test_legacy_selector_flow_skips_when_excel_target_has_a_priced_offer() -> None:
    bot = _bot()
    bot.selectors = SimpleNamespace(
        item_search_input="[data-item-search]",
        item_first_result="",
        qty_input="[data-qty]",
        add_item_button="[data-add]",
        warehouse_rows="[data-warehouse-row]",
        warehouse_available_qty="[data-available]",
        warehouse_pick_button="[data-pick]",
        new_order="",
    )
    processor = OrderItemProcessor(bot)
    decision = CartGateDecision(False, 90.0, "")
    page = Mock()

    with patch(
        "src.tawreed.order.tawreed_order_processing.ExcelTargetCartGate.evaluate",
        return_value=decision,
    ):
        with pytest.raises(RuntimeError, match="deferred_to_excel_target"):
            processor.add_item_with_configured_flow(page, ITEM)

    page.locator.assert_any_call(bot.selectors.item_search_input)
    assert not any(
        call.args == (bot.selectors.add_item_button,)
        for call in page.locator.call_args_list
    )
