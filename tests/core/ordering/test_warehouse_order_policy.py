from __future__ import annotations

import pytest

from src.core.ordering.warehouse_order_policy import (
    excel_target_blocks_tawreed,
    plan_tawreed_allocations,
)


def _tawreed(
    name: str, price: float, stock: int, discount_percent: float = 0.0
) -> dict:
    return {
        "storeName": name,
        "storeProductId": name,
        "salePrice": price,
        "retailPrice": price,
        "availableQuantity": stock,
        "discountPercent": discount_percent,
    }


def _excel(
    price: float, stock: int = 1, discount_percent: float = 0.0
) -> dict:
    return {
        "storeName": "Excel Target",
        "storeProductId": "excel-1",
        "purchase_price": price,
        "available_qty": stock,
        "discount_percent": discount_percent,
    }


@pytest.mark.parametrize(
    ("excel", "tawreed", "blocked"),
    [(90.0, 100.0, True), (100.0, 100.0, True),
     (100.24, 100.0, True), (100.25, 100.0, False)],
)
def test_excel_target_gate_uses_strict_quarter_egp_threshold(
    excel: float, tawreed: float, blocked: bool
) -> None:
    assert excel_target_blocks_tawreed(excel, tawreed) is blocked


def test_missing_price_never_blocks() -> None:
    assert excel_target_blocks_tawreed(None, 100.0) is False
    assert excel_target_blocks_tawreed(100.0, None) is False


def test_lowest_purchase_price_uses_price_then_preference_and_fills_quantity() -> None:
    plan = plan_tawreed_allocations(
        10,
        [
            _tawreed("unlisted", 100.0, 10),
            _tawreed("baraka", 100.0, 7),
            _tawreed("alpha", 100.0, 3),
        ],
        mode="lowest_purchase_price",
        preferred_warehouses=["baraka", "alpha"],
    )

    assert [line.store["storeName"] for line in plan.allocations] == [
        "baraka", "alpha"
    ]
    assert [line.quantity for line in plan.allocations] == [7, 3]
    assert plan.remaining_qty == 0


def test_alpha_wins_from_lowest_price_and_existing_rank() -> None:
    plan = plan_tawreed_allocations(
        1,
        [
            _tawreed("شركه البركه (الجيزه)", 18.40, 18),
            _tawreed("شركه عنايه للادويه (الجيزه)", 18.20, 54),
            _tawreed("شركة الفا فارما (الجيزه)", 18.20, 53),
            _tawreed("شركه التحرير (الجيزه)", 18.48, 5),
        ],
        mode="lowest_purchase_price",
        preferred_warehouses=[
            "شركه البركه (الجيزه)",
            "شركه الماسه (مالك سابقا ) (الجيزه)",
            "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)",
            "شركه الفا فارما (الجيزه)",
        ],
    )

    assert plan.allocations[0].store["storeName"] == "شركة الفا فارما (الجيزه)"


def test_cheapest_warehouse_wins_a_price_gap_below_025() -> None:
    plan = plan_tawreed_allocations(
        1,
        [
            _tawreed("شركه عنايه", 100.0, 10),
            _tawreed("شركه البركه", 100.20, 10),
        ],
        mode="lowest_purchase_price",
        preferred_warehouses=["شركه البركه"],
    )

    assert plan.allocations[0].store["storeName"] == "شركه عنايه"


def test_cheapest_offer_wins_at_exact_quarter_price_gap() -> None:
    plan = plan_tawreed_allocations(
        1,
        [
            _tawreed("شركه البركه", 100.25, 10),
            _tawreed("شركه الفا فارما", 100.0, 10),
        ],
        mode="lowest_purchase_price",
        preferred_warehouses=["شركه البركه", "شركه الفا فارما"],
    )

    assert plan.allocations[0].store["storeName"] == "شركه الفا فارما"


def test_lowest_purchase_price_uses_price_within_same_preference_rank() -> None:
    plan = plan_tawreed_allocations(
        1,
        [_tawreed("same-rank", 100.25, 5), _tawreed("same-rank", 100.0, 5)],
        mode="lowest_purchase_price",
        preferred_warehouses=["same-rank"],
    )

    assert plan.allocations[0].store["salePrice"] == 100.0


def test_ineligible_preferred_warehouse_falls_back_to_next_available() -> None:
    plan = plan_tawreed_allocations(
        2,
        [
            _tawreed("alpha", 18.48, 0),
            _tawreed("unlisted", 18.20, 10),
        ],
        mode="lowest_purchase_price",
        preferred_warehouses=["alpha"],
    )

    assert [line.store["storeName"] for line in plan.allocations] == ["unlisted"]


def test_excel_target_blocks_before_any_tawreed_allocation() -> None:
    plan = plan_tawreed_allocations(
        4,
        [_tawreed("first", 100.0, 4)],
        mode="lowest_purchase_price",
        excel_offers=[_excel(100.20)],
    )

    assert plan.blocked_by_excel_target is True
    assert plan.allocations == ()
    assert plan.remaining_qty == 4
    assert plan.reason == "deferred_to_excel_target"


def test_minimum_discount_filters_tawreed_and_excel_target() -> None:
    below_threshold = plan_tawreed_allocations(
        1,
        [_tawreed("Tawreed below threshold", 100.0, 4, discount_percent=9.0)],
        min_discount_percent=10.0,
        excel_offers=[_excel(80.0, discount_percent=10.0)],
    )
    eligible_tawreed = plan_tawreed_allocations(
        1,
        [_tawreed("Tawreed eligible", 100.0, 4, discount_percent=10.0)],
        min_discount_percent=10.0,
        excel_offers=[_excel(80.0, discount_percent=9.0)],
    )
    every_offer_below_threshold = plan_tawreed_allocations(
        1,
        [_tawreed("Tawreed below threshold", 100.0, 4, discount_percent=9.0)],
        min_discount_percent=10.0,
        excel_offers=[_excel(80.0, discount_percent=9.0)],
    )

    assert below_threshold.blocked_by_excel_target is True
    assert below_threshold.reason == "deferred_to_excel_target"
    assert below_threshold.allocations == ()
    assert eligible_tawreed.blocked_by_excel_target is False
    assert eligible_tawreed.allocations[0].store["storeName"] == "Tawreed eligible"
    assert every_offer_below_threshold.blocked_by_excel_target is False
    assert every_offer_below_threshold.allocations == ()


def test_invalid_or_empty_offers_are_not_allocated() -> None:
    plan = plan_tawreed_allocations(
        2,
        [_tawreed("empty", 100.0, 0), _tawreed("unpriced", 0.0, 10)],
    )

    assert plan.allocations == ()
    assert plan.remaining_qty == 2


def test_removed_warehouse_modes_are_rejected() -> None:
    with pytest.raises(ValueError, match="Only lowest_purchase_price"):
        plan_tawreed_allocations(
            1,
            [_tawreed("store", 10.0, 1)],
            mode="max_discount",
        )
