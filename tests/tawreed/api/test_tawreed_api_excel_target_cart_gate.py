"""Regression tests for the API Excel Target cart gate."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.ordering.excel_target_cart_gate import CartGateDecision
from src.core.utils.excel import Item
from src.tawreed.api.tawreed_api_flow_cart import _add_single_item_to_cart
from src.tawreed.api.tawreed_api_flow_multistore import (
    _select_stores_and_add_to_cart,
)
from src.tawreed.order.tawreed_order_placement import _SkipItem


def _bot(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        skip_item_exception=_SkipItem,
        last_ordered_total_qty=0,
        match_only=False,
        config=SimpleNamespace(
            database=SimpleNamespace(order_runs_path=str(tmp_path / "runs.db")),
            warehouse_strategy={"mode": "first_available"},
        ),
    )


def test_api_gate_prefers_explicit_shared_scope_over_active_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All profiles in a combined run must query the shared Excel run key."""
    from src.tawreed.api import tawreed_api_flow_cart as flow

    bot = _bot(tmp_path)
    bot.config.excel_target_cart_gate_run_key = "wardany/shared-run"
    monkeypatch.setattr(
        "src.tawreed.store.tawreed_store_run_payload.active_order_run_key",
        lambda: "second-profile/active-run",
    )
    seen: list[str] = []

    def evaluate(_self, run_key, _item, _store):
        seen.append(run_key)
        return CartGateDecision(False, 101.0, "")

    monkeypatch.setattr(flow.ExcelTargetCartGate, "evaluate", evaluate)
    api = MagicMock()
    _add_single_item_to_cart(
        bot,
        api,
        SimpleNamespace(data=_store(100.0)),
        Item(code="1", name="PANADOL", qty=1),
        lambda *_a: None,
    )

    assert seen == ["wardany/shared-run"]
    api.add_to_cart.assert_called_once()


def test_api_cart_gate_is_bypassed_when_persistence_is_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Disabling order-run persistence must preserve normal cart behavior."""
    from src.tawreed.api import tawreed_api_flow_cart as flow

    bot = _bot(tmp_path)
    bot.config.database.order_runs_enabled = False
    monkeypatch.setattr(
        flow.ExcelTargetCartGate,
        "evaluate",
        lambda *_args: (_ for _ in ()).throw(AssertionError("gate called")),
    )
    api = MagicMock()
    _add_single_item_to_cart(
        bot,
        api,
        SimpleNamespace(data=_store(100.0)),
        Item(code="1", name="PANADOL", qty=1),
        lambda *_a: None,
    )

    api.add_to_cart.assert_called_once()


def _store(price: float, store_id: str = "store-1") -> dict:
    return {
        "storeProductId": store_id,
        "storeName": "Store",
        "availableQuantity": 10,
        "retailPrice": price,
        "salePrice": price,
        "discountPercent": 0,
    }


def test_api_single_store_does_not_add_when_excel_price_is_equal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The single-store API mutation is skipped when Excel is as cheap."""
    from src.tawreed.api import tawreed_api_flow_cart as flow

    monkeypatch.setattr(
        "src.tawreed.store.tawreed_store_run_payload.active_order_run_key",
        lambda: "wardany/run-1",
    )
    monkeypatch.setattr(
        flow.ExcelTargetCartGate,
        "evaluate",
        lambda self, run_key, item, store: CartGateDecision(
            True,
            100.0,
            "Excel Target purchase price 100.00 is lower than or within 0.25 EGP of Tawreed purchase price 100.00",
        ),
    )
    bot = _bot(tmp_path)
    api = MagicMock()
    match = SimpleNamespace(data=_store(100.0))

    with pytest.raises(_SkipItem, match="deferred_to_excel_target"):
        _add_single_item_to_cart(
            bot, api, match, Item(code="1", name="PANADOL", qty=1), lambda *_a: None
        )

    api.add_to_cart.assert_not_called()


def test_api_single_store_below_configured_discount_floor_is_not_added(
    tmp_path: Path,
) -> None:
    """Reject an ineligible Tawreed offer even when the price gate is inactive."""
    bot = _bot(tmp_path)
    bot.config.warehouse_strategy["min_discount_percent"] = 10.0
    api = MagicMock()

    with pytest.raises(_SkipItem, match="below the configured minimum"):
        _add_single_item_to_cart(
            bot,
            api,
            SimpleNamespace(data=_store(100.0)),
            Item(code="1", name="PANADOL", qty=1),
            lambda *_a: None,
        )

    api.add_to_cart.assert_not_called()


def test_api_lowest_price_skips_when_all_tawreed_offers_miss_floor(
    tmp_path: Path,
) -> None:
    """Lowest-price mode must not add a below-floor store."""
    bot = _bot(tmp_path)
    bot.config.warehouse_strategy.update(
        mode="lowest_purchase_price", min_discount_percent=10.0
    )
    api = MagicMock()
    store_rows = [
        {**_store(100.0, "store-1"), "discountPercent": 8.0},
        {**_store(101.0, "store-2"), "discountPercent": 9.0},
    ]

    with pytest.raises(_SkipItem, match="out of stock or unpriced"):
        _select_stores_and_add_to_cart(
            bot,
            api,
            Item(code="1", name="PANADOL", qty=1),
            store_rows,
            [],
            lambda *_a: None,
        )

    api.add_to_cart.assert_not_called()


def test_api_multistore_preflights_all_choices_before_any_add(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocked item is rejected before any store allocation is added."""
    from src.tawreed.api import tawreed_api_flow_cart as cart_flow

    monkeypatch.setattr(
        "src.tawreed.store.tawreed_store_run_payload.active_order_run_key",
        lambda: "wardany/run-1",
    )
    calls: list[int] = []

    def evaluate_candidates(_self, _run_key, _item, stores, **_kwargs):
        calls.append(len(stores))
        return CartGateDecision(True, 90.0, "Excel Target price wins")

    monkeypatch.setattr(
        cart_flow.ExcelTargetCartGate, "evaluate_candidates", evaluate_candidates
    )
    bot = _bot(tmp_path)
    api = MagicMock()
    item = Item(code="1", name="PANADOL", qty=15)
    store_rows = [_store(100.0, "store-1"), _store(101.0, "store-2")]

    with pytest.raises(_SkipItem, match="Excel Target"):
        _select_stores_and_add_to_cart(
            bot,
            api,
            item,
            store_rows,
            [],
            lambda *_a: None,
        )

    assert calls == [2]
    api.add_to_cart.assert_not_called()
