from __future__ import annotations

from src.ui.views.run_db.match_only_purchase_simulation import (
    build_match_only_purchase_simulation,
)


def _base_row(**overrides) -> dict:
    row = {
        "run_mode": "match-only",
        "warehouse_mode": "first_available",
        "min_discount_pct": 0,
        "item_key": "A::ITEM A",
        "item_code": "A",
        "item_name": "ITEM A",
        "requested_qty": 5,
        "status": "matched-only",
        "matched": 1,
        "manual_review_required": 0,
        "matched_name": "Matched item A",
        "excel_matched": 1,
        "excel_manual_review_required": 0,
    }
    row.update(overrides)
    return row


def _tawreed_offer(
    name: str,
    product_id: str,
    available: int,
    price: float,
    *,
    is_winner: int = 0,
    snapshot_order: int = 1,
) -> dict:
    return _base_row(
        store_name=name,
        store_product_id=product_id,
        store_key=f"store:{name}",
        source="store_details",
        source_label="wardany",
        available_qty=available,
        public_price=price * 1.25,
        purchase_price=price,
        discount_percent=20,
        is_winner=is_winner,
        snapshot_order=snapshot_order,
    )


def test_match_only_simulates_multi_store_quantities_from_captured_stock() -> None:
    simulation = build_match_only_purchase_simulation(
        [
            _tawreed_offer("Warehouse A", "a", 2, 10.0, is_winner=1),
            _tawreed_offer("Warehouse B", "b", 8, 11.0, snapshot_order=2),
        ]
    )

    assert simulation is not None
    assert [(row["store_name"], row["simulated_qty"]) for row in simulation.tawreed_rows] == [
        ("Warehouse A", 2),
        ("Warehouse B", 3),
    ]
    assert all(row["unfilled_qty"] == 0 for row in simulation.tawreed_rows)
    assert simulation.excel_target_rows == []


def test_match_only_first_available_uses_lowest_price_then_existing_preference() -> None:
    simulation = build_match_only_purchase_simulation(
        [
            _tawreed_offer(
                "شركه البركه (الجيزه)", "baraka", 18, 18.76,
                snapshot_order=1,
            ),
            _tawreed_offer(
                "شركه عنايه للادويه (الجيزه)", "enaya", 54, 18.20,
                snapshot_order=2,
            ),
            _tawreed_offer(
                "شركة الفا فارما (الجيزه)", "alpha", 53, 18.20,
                snapshot_order=3,
            ),
            _tawreed_offer(
                "شركه التحرير (الجيزه)", "tahrir", 5, 18.48,
                snapshot_order=4,
            ),
        ]
    )

    assert simulation is not None
    assert [(row["store_name"], row["simulated_qty"]) for row in simulation.tawreed_rows] == [
        ("شركة الفا فارما (الجيزه)", 5)
    ]


def test_excel_target_within_quarter_pound_is_simulated_outside_tawreed() -> None:
    tawreed = _tawreed_offer("Warehouse A", "a", 8, 10.0, is_winner=1)
    excel = _base_row(
        store_name="excel-target:البركة شركات@البركة شركات.xlsx",
        store_key="excel-target:البركة شركات@البركة شركات.xlsx",
        store_product_id="excel-a",
        source="excel_target",
        source_label="البركة شركات@البركة شركات.xlsx",
        available_qty=1,
        public_price=10.2,
        purchase_price=10.2,
        discount_percent=5,
        is_winner=0,
    )

    simulation = build_match_only_purchase_simulation([tawreed, excel])

    assert simulation is not None
    assert simulation.tawreed_rows == []
    assert len(simulation.excel_target_rows) == 1
    assert simulation.excel_target_rows[0]["excel_target_source"].startswith(
        "البركة شركات@"
    )
    assert simulation.excel_target_rows[0]["simulated_qty"] == 1


def test_simulation_filters_excel_discount_and_shows_the_eligible_offer() -> None:
    tawreed = _tawreed_offer("Tawreed", "tawreed", 8, 9.0) | {
        "discount_percent": 0.0,
        "min_discount_pct": 10.0,
    }
    cheap_ineligible_excel = _base_row(
        store_name="excel-target:target@Cheap.xlsx",
        store_key="excel-target:target@Cheap.xlsx",
        store_product_id="cheap-excel",
        source="excel_target",
        source_label="target@Cheap.xlsx",
        available_qty=1,
        purchase_price=8.0,
        discount_percent=9.0,
    )
    eligible_excel = _base_row(
        store_name="excel-target:target@Eligible.xlsx",
        store_key="excel-target:target@Eligible.xlsx",
        store_product_id="eligible-excel",
        source="excel_target",
        source_label="target@Eligible.xlsx",
        available_qty=1,
        purchase_price=9.1,
        discount_percent=10.0,
    )

    simulation = build_match_only_purchase_simulation(
        [tawreed, cheap_ineligible_excel, eligible_excel]
    )

    assert simulation is not None
    assert simulation.tawreed_rows == []
    assert simulation.excel_target_rows[0]["excel_target_source"] == "target@Eligible.xlsx"
    assert simulation.excel_target_rows[0]["purchase_price"] == 9.1


def test_exactly_quarter_pound_difference_does_not_trigger_excel_gate() -> None:
    tawreed = _tawreed_offer("Warehouse A", "a", 8, 10.0, is_winner=1)
    excel = _base_row(
        store_name="excel-target:البركة شركات@البركة شركات.xlsx",
        store_key="excel-target:البركة شركات@البركة شركات.xlsx",
        store_product_id="excel-a",
        source="excel_target",
        source_label="البركة شركات@البركة شركات.xlsx",
        available_qty=1,
        public_price=10.25,
        purchase_price=10.25,
        discount_percent=5,
        is_winner=0,
    )

    simulation = build_match_only_purchase_simulation([tawreed, excel])

    assert simulation is not None
    assert [row["store_name"] for row in simulation.tawreed_rows] == ["Warehouse A"]
    assert simulation.excel_target_rows == []


def test_manual_review_items_are_not_presented_as_simulated_orders() -> None:
    simulation = build_match_only_purchase_simulation(
        [
            _tawreed_offer(
                "Warehouse A", "a", 8, 10.0, is_winner=1,
            ) | {"manual_review_required": 1},
        ]
    )

    assert simulation is not None
    assert simulation.tawreed_rows == []
    assert simulation.manual_review_items == 1


def test_other_run_modes_do_not_create_hypothetical_baskets() -> None:
    assert build_match_only_purchase_simulation(
        [_tawreed_offer("Warehouse A", "a", 8, 10.0) | {"run_mode": "order"}]
    ) is None


def test_historical_warehouse_strategy_is_replayed_with_lowest_price() -> None:
    simulation = build_match_only_purchase_simulation(
        [
            _tawreed_offer("Warehouse A", "a", 8, 10.0)
            | {"warehouse_mode": "max_available"}
        ]
    )

    assert simulation is not None
    assert len(simulation.tawreed_rows) == 1
    assert simulation.unsupported_strategy_items == 0
