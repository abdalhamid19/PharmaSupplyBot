from __future__ import annotations

from pathlib import Path

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_read import (
    fetch_run_actual_basket,
    fetch_run_deferred_excel,
)
from src.core.database.order_runs_store import OrderRunsStore


def _store(name: str, product_id: str, price: float) -> dict:
    return {
        "storeName": name,
        "storeId": name,
        "storeProductId": product_id,
        "availableQuantity": 10,
        "retailPrice": price + 2,
        "salePrice": price,
    }


def test_actual_basket_uses_ordered_quantity_not_price_winner(tmp_path: Path) -> None:
    store = OrderRunsStore(tmp_path / "runs.db")
    run_key = "tester/20260101_1200"
    store.open_run(
        run_meta_row("tester", "20260101_1200", "2026-01-01T12:00:00Z")
    )
    price_winner = _store("Price winner", "price", 90.0)
    selected = _store("Selected store", "selected", 100.0)
    store.upsert_run_item(
        run_key,
        {
            "item_code": "1",
            "item_name": "ITEM",
            "item_qty": 3,
            "ordered_total_qty": 2,
            "status": "added-to-cart",
            "matched": 1,
        },
        source_kind="tawreed",
        source_label="tester",
        stores=[price_winner, selected],
        store_source="store_details",
        store_selections=[(selected, 2)],
    )

    rows = fetch_run_actual_basket(run_key, db=store.db.path)

    assert len(rows) == 1
    assert rows[0]["store_name"] == "Selected store"
    assert rows[0]["ordered_qty"] == 2


def test_deferred_excel_reports_lowest_excel_source_even_without_global_winner(
    tmp_path: Path,
) -> None:
    store = OrderRunsStore(tmp_path / "runs.db")
    run_key = "tester/20260101_1200"
    store.open_run(
        run_meta_row("tester", "20260101_1200", "2026-01-01T12:00:00Z")
    )
    excel_offer = _store("Excel target", "excel-product", 90.0)
    store.upsert_run_item(
        run_key,
        {
            "item_code": "1", "item_name": "ITEM", "item_qty": 1,
            "matched_product_name_ar": "اسم القيصر المطابق",
        },
        source_kind="excel-target",
        source_label="القيصر شركات@القيصر.xlsx",
        stores=[excel_offer],
        store_selections=[],
        store_source="excel_target",
    )
    store.upsert_run_item(
        run_key,
        {
            "item_code": "1", "item_name": "ITEM", "item_qty": 1,
            "status": "deferred-to-excel-target",
        },
        source_kind="tawreed",
        source_label="wardany",
    )

    rows = fetch_run_deferred_excel(run_key, db=store.db.path)

    assert len(rows) == 1
    assert rows[0]["excel_target_source"] == "القيصر شركات@القيصر.xlsx"
    assert rows[0]["excel_purchase_price"] == 90.0
    assert rows[0]["matched_name"] == "اسم القيصر المطابق"
