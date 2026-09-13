"""Configured discount-floor enforcement in Tawreed match-only runtime paths."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.tawreed.api.tawreed_api_match_only_metadata import (
    api_match_only_store_choice,
    record_api_match_only_store_metadata,
)
from src.tawreed.products.tawreed_match_only_metadata import (
    choose_match_only_store,
    record_match_only_store_metadata,
)
from src.tawreed.store.tawreed_store_snapshot import captured_store_selections


def _bot(minimum: float = 10.0) -> SimpleNamespace:
    return SimpleNamespace(
        skip_item_exception=RuntimeError,
        config=SimpleNamespace(
            warehouse_strategy={
                "mode": "lowest_purchase_price",
                "min_discount_percent": minimum,
            }
        ),
    )


def _store(discount: float, **extra) -> dict:
    return {
        "storeProductId": "store-1",
        "storeName": "Store",
        "availableQuantity": 5,
        "discountPercent": discount,
        **extra,
    }


def test_single_store_browser_match_only_rejects_below_floor_before_recording():
    bot = _bot()
    match = SimpleNamespace(data=_store(8.0, productsCount=0))

    with patch(
        "src.tawreed.store.tawreed_store_summary.record_single_store"
    ) as record:
        with pytest.raises(RuntimeError, match="below the configured minimum"):
            record_match_only_store_metadata(bot, object(), match, None)

    record.assert_not_called()
    assert captured_store_selections(bot) == []


def test_single_store_api_match_only_rejects_below_floor_before_recording():
    bot = _bot()
    match = SimpleNamespace(data=_store(8.0, productsCount=0))

    with patch(
        "src.tawreed.store.tawreed_store_summary.record_single_store"
    ) as record:
        with pytest.raises(RuntimeError, match="below the configured minimum"):
            record_api_match_only_store_metadata(bot, MagicMock(), match)

    record.assert_not_called()
    assert captured_store_selections(bot) == []


def test_browser_match_only_propagates_when_all_store_rows_miss_floor():
    bot = _bot()
    match = SimpleNamespace(data=_store(8.0, productsCount=2))

    with patch(
        "src.tawreed.products.tawreed_match_only_metadata.match_only_store_rows",
        return_value=[_store(8.0), _store(9.0, storeProductId="store-2")],
    ):
        with pytest.raises(RuntimeError, match="minimum discount 10%"):
            record_match_only_store_metadata(bot, object(), match, None)

    assert captured_store_selections(bot) == []


def test_api_match_only_filters_multi_store_choices_by_configured_floor():
    bot = _bot()
    api = MagicMock()
    api.get_store_details.return_value = [
        _store(8.0),
        _store(9.0, storeProductId="store-2"),
    ]

    with pytest.raises(RuntimeError, match="minimum discount 10%"):
        api_match_only_store_choice(bot, api, {"productId": "product-1"})


def test_match_only_store_selector_uses_floor_in_lowest_purchase_price_mode():
    bot = _bot()
    stores = [
        _store(8.0, purchase_price=10.0),
        _store(12.0, storeProductId="store-2", purchase_price=9.0),
    ]

    choice = choose_match_only_store(bot, stores)

    assert choice is not None
    assert choice.store["storeProductId"] == "store-2"
