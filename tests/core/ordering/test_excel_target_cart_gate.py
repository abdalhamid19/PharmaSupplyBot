"""Focused tests for the Excel Target cart price gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_store import OrderRunsStore
from src.core.utils.excel import Item


RUN_KEY = "wardany/run-1"
ITEM = Item(code="12345", name="CAL MAG", qty=1)


def _offer(
    product_id: int,
    public_price: float | None,
    discount_percent: float = 0.0,
) -> dict:
    """Build the small candidate shape persisted by the Excel Target flow."""
    return {
        "storeId": product_id,
        "storeName": f"Excel Target {product_id}",
        "storeProductId": product_id,
        "productId": product_id,
        "productName": ITEM.name,
        "availableQuantity": 10,
        "retailPrice": public_price,
        "discountPercent": discount_percent,
    }


def _write_excel_offers(
    db_path: Path,
    offers: list[dict],
    *,
    item: Item = ITEM,
    run_key: str = RUN_KEY,
) -> None:
    """Persist accepted Excel Target offers into an isolated order-run DB."""
    store = OrderRunsStore(db_path)
    store.open_run(run_meta_row("wardany", "run-1", started_at="2026-09-09T12:00:00"))
    store.upsert_run_item(
        run_key,
        {
            "item_code": item.code,
            "item_name": item.name,
            "item_qty": item.qty,
            "status": "matched-only",
            "matched": True,
        },
        stores=offers,
        store_source="excel_target",
    )


def _tawreed_store(purchase_price: float | None) -> dict:
    """Build a Tawreed candidate whose sale price is its purchase price."""
    return {
        "storeProductId": "tawreed-1",
        "retailPrice": purchase_price,
        "salePrice": purchase_price,
    }


def test_blocks_when_excel_purchase_price_is_lower_or_equal(tmp_path: Path) -> None:
    """An equal or cheaper accepted Excel offer prevents a cart addition."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(db_path, [_offer(1, public_price=100.0)])
    gate = ExcelTargetCartGate(db_path)

    lower = gate.evaluate(RUN_KEY, ITEM, _tawreed_store(101.0))
    equal = gate.evaluate(RUN_KEY, ITEM, _tawreed_store(100.0))

    assert lower.blocked is True
    assert equal.blocked is True
    assert lower.excel_purchase_price == 100.0
    assert "Excel Target" in lower.reason


def test_allows_when_excel_purchase_price_is_higher(tmp_path: Path) -> None:
    """A more expensive Excel offer does not block the Tawreed candidate."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(db_path, [_offer(1, public_price=101.0)])

    decision = ExcelTargetCartGate(db_path).evaluate(
        RUN_KEY, ITEM, _tawreed_store(100.0)
    )

    assert decision.blocked is False
    assert decision.excel_purchase_price == 101.0
    assert decision.reason == ""


def test_uses_lowest_resolved_excel_purchase_price_and_ignores_raw_public_price(
    tmp_path: Path,
) -> None:
    """The comparison uses persisted purchase prices after discount resolution."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(
        db_path,
        [
            _offer(1, public_price=200.0, discount_percent=10.0),
            _offer(2, public_price=150.0, discount_percent=50.0),
        ],
    )

    decision = ExcelTargetCartGate(db_path).evaluate(
        RUN_KEY, ITEM, _tawreed_store(80.0)
    )

    # The persisted prices are 180 and 75; comparing raw public prices would
    # incorrectly allow the Tawreed offer because 150 is greater than 80.
    assert decision.excel_purchase_price == 75.0
    assert decision.blocked is True


def test_null_excel_purchase_price_never_blocks(tmp_path: Path) -> None:
    """Rows without a resolved Excel purchase price are not comparable."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(db_path, [_offer(1, public_price=None)])

    decision = ExcelTargetCartGate(db_path).evaluate(
        RUN_KEY, ITEM, _tawreed_store(1.0)
    )

    assert decision.blocked is False
    assert decision.excel_purchase_price is None


def test_missing_or_unpriced_tawreed_candidate_never_blocks(tmp_path: Path) -> None:
    """A missing Tawreed purchase price cannot satisfy the price comparison."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(db_path, [_offer(1, public_price=1.0)])

    decision = ExcelTargetCartGate(db_path).evaluate(RUN_KEY, ITEM, {})

    assert decision.blocked is False
    assert decision.excel_purchase_price == 1.0


def test_gate_uses_item_dimension_key_and_run_key_scope(tmp_path: Path) -> None:
    """Offers from another item or run cannot block the requested candidate."""
    from src.core.ordering.excel_target_cart_gate import ExcelTargetCartGate

    db_path = tmp_path / "runs.db"
    _write_excel_offers(
        db_path,
        [_offer(1, public_price=1.0)],
        item=Item(code="999", name="OTHER", qty=1),
        run_key="wardany/run-1",
    )
    gate = ExcelTargetCartGate(db_path)

    decision = gate.evaluate(RUN_KEY, ITEM, _tawreed_store(100.0))

    assert decision.blocked is False
    assert decision.excel_purchase_price is None
