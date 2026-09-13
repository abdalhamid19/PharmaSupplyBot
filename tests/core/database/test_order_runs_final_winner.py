from __future__ import annotations

from pathlib import Path

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_read import fetch_run_deferred_excel
from src.core.database.order_runs_store import OrderRunsStore


def _store(
    name: str, product_id: str, price: float, discount: float = 0.0
) -> dict:
    return {
        "storeName": name,
        "storeId": name,
        "storeProductId": product_id,
        "availableQuantity": 10,
        "retailPrice": 100,
        "salePrice": price,
        "discountPercent": discount,
    }


def _excel_offer(
    name: str, product_id: str, purchase_price: float, discount: float
) -> dict:
    """Build an Excel purchase-only offer with a structured discount field."""
    return {
        "storeName": name,
        "storeId": name,
        "storeProductId": product_id,
        "availableQuantity": 10,
        "salePrice": purchase_price,
        "discountPercent": discount,
        "priceMeaning": "purchase_only",
    }


def test_excel_deferred_item_marks_excel_offer_as_only_final_winner(
    tmp_path: Path,
) -> None:
    store = OrderRunsStore(tmp_path / "runs.db")
    run_key = "tester/20260101_1200"
    store.open_run(
        run_meta_row(
            "tester", "20260101_1200", "2026-01-01T12:00:00Z",
            min_discount_pct=10.0,
        )
    )
    excel = _excel_offer("Eligible Excel", "eligible-excel", 68.31, discount=10.0)
    cheap_ineligible_excel = _excel_offer("Cheap Excel", "cheap-excel", 60.0, discount=9.0)
    tawreed = _store("Rayyan", "rayyan", 68.29)
    store.upsert_run_item(
        run_key,
        {"item_code": "1", "item_name": "ITEM", "item_qty": 1},
        source_kind="excel-target",
        source_label="القيصر شركات@القيصر.xlsx",
        stores=[excel, cheap_ineligible_excel],
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
        stores=[tawreed],
        store_selections=[(tawreed, 0)],
        store_source="store_details",
    )

    winners = store.db.execute_query(
        "select source, discount_percent from run_item_stores "
        "where run_key=? and is_winner=1",
        (run_key,),
    )

    assert winners == [("excel_target", 10.0)]
    deferred = fetch_run_deferred_excel(run_key, db=store.path)
    assert len(deferred) == 1
    assert deferred[0]["excel_purchase_price"] == 68.31
    assert deferred[0]["excel_discount_percent"] == 10.0
