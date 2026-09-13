"""Price comparison, persistence, retries and old-run upgrade coverage."""

from itertools import permutations
import sqlite3

import pytest

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_read import fetch_run_warehouse_winners, fetch_run_warehouse_exclusions
from src.core.database.order_runs_store import OrderRunsStore
from src.core.database.warehouse_winner_selection import PREFERRED_WAREHOUSES, select_warehouse_winner


def offer(name="Other", price=8, source="tawreed", **values):
    return dict(store_name=name, store_key=name, store_product_id=name,
                purchase_price=price, available_qty=2, source=source, currency="", **values)


def test_price_precedes_source_and_preference():
    rows = [offer("Excel", 9, "excel_target"), offer(PREFERRED_WAREHOUSES[0], 10), offer()]
    assert select_warehouse_winner(rows)[0]["store_name"] == "Other"
    assert select_warehouse_winner([offer(), offer("Excel", 8, "excel_target")])[1] == "excel_preferred"


def test_tawreed_nearby_prices_choose_the_cheapest_offer():
    rows = [
        offer(PREFERRED_WAREHOUSES[1], 100.0),
        offer(PREFERRED_WAREHOUSES[0], 100.2),
    ]
    assert select_warehouse_winner(rows)[0]["store_name"] == PREFERRED_WAREHOUSES[1]


def test_minimum_discount_filters_tawreed_and_excel_target():
    rows = [
        offer("Tawreed below threshold", 7, discount_percent=9),
        offer("Excel below threshold", 5, "excel_target", discount_percent=9),
        offer("Excel eligible", 8, "excel_target", discount_percent=10),
    ]
    winner, _reason = select_warehouse_winner(rows, min_discount_percent=10)
    assert winner["store_name"] == "Excel eligible"
    winner, _reason = select_warehouse_winner(
        [
            offer("Tawreed eligible", 7, discount_percent=10),
            offer("Excel below threshold", 5, "excel_target", discount_percent=9),
            offer("Excel eligible", 8, "excel_target", discount_percent=10),
        ],
        min_discount_percent=10,
    )
    assert winner["store_name"] == "Tawreed eligible"
    assert select_warehouse_winner(
        [offer("Tawreed below", 7, discount_percent=9)],
        min_discount_percent=10,
    )[0] is None


def test_tawreed_exact_lowest_price_wins_at_quarter_gap():
    rows = [
        offer(PREFERRED_WAREHOUSES[0], 100.25),
        offer(PREFERRED_WAREHOUSES[1], 100.0),
    ]
    assert select_warehouse_winner(rows)[0]["store_name"] == PREFERRED_WAREHOUSES[1]


def test_cross_source_comparison_keeps_exact_price_rule():
    rows = [
        offer("Excel", 100.5, "excel_target"),
        offer("Tawreed", 100.0, "store_details"),
    ]
    assert select_warehouse_winner(rows)[0]["store_name"] == "Tawreed"


@pytest.mark.parametrize("index", range(7))
def test_preferred_warehouse_order(index):
    rows = [offer(name) for name in PREFERRED_WAREHOUSES[index:]] + [offer()]
    assert select_warehouse_winner(rows[::-1])[0]["store_name"] == PREFERRED_WAREHOUSES[index]


def test_stable_ties_and_currency_metadata_does_not_exclude_offers():
    rows = [offer("B", source="excel_target"), offer("A", source="excel-target")]
    for order in permutations(rows):
        assert select_warehouse_winner(list(order))[0]["store_name"] == "A"
    rows = [
        dict(offer("Egyptian currency", 8), currency="?.?"),
        dict(offer("Legacy currency text", 7), currency="USD"),
    ]
    assert select_warehouse_winner(rows)[0]["store_name"] == "Legacy currency text"


def test_excel_ties_do_not_use_tawreed_preference_names():
    rows = [
        offer(PREFERRED_WAREHOUSES[0], source="excel_target"),
        offer("A.xlsx", source="excel_target"),
    ]
    assert select_warehouse_winner(rows)[0]["store_name"] == "A.xlsx"


@pytest.mark.parametrize("price", [None, 0, -1, float("nan"), float("inf"), "bad"])
def test_invalid_prices(price):
    assert select_warehouse_winner([offer(price=price)])[0] is None


def test_unavailable_is_excluded():
    rows = [dict(offer("zero", 1), available_qty=0), offer()]
    assert select_warehouse_winner(rows)[0]["store_name"] == "Other"


@pytest.fixture
def store(tmp_path):
    result = OrderRunsStore(tmp_path / "runs.db")
    result.open_run(run_meta_row("test", "one", "2026-09-08"))
    yield result
    result.db.close()


def persist(store, name, price, source="store_details", qty=2, discount=0):
    candidate = dict(storeProductId="same-code", storeName=name,
                     productName="Supplier product", availableQuantity=qty,
                     retailPrice=price, salePrice=price, discountPercent=discount,
                     priceMeaning="purchase_only")
    store.upsert_run_item(
        "test/one", dict(item_code="001", item_name="Drug", item_qty=10, status="matched-only"),
        stores=[candidate], store_source=source,
        source_kind="excel-target" if source == "excel_target" else "tawreed",
        source_label=name.removeprefix("excel-target:"),
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_multiple_catalogs_arrival_retry_and_reopen(store, reverse):
    rows = [("Tawreed", 8, "store_details"),
            ("excel-target:baraka@البركة شركات.xlsx", 8, "excel_target"),
            ("excel-target:other@Other.xlsx", 9, "excel_target")]
    for args in rows[::-1] if reverse else rows:
        persist(store, *args)
    winners = fetch_run_warehouse_winners("test/one", store.path)
    assert len(winners) == 1
    assert winners[0]["store_name"] == "البركة شركات.xlsx"
    assert winners[0]["requested_qty"] == 10
    assert winners[0]["available_qty"] == 2
    assert store.count_run_item_stores("test/one", winners[0]["item_key"]) == 3
    persist(store, rows[1][0], 8, "excel_target", qty=0)
    assert fetch_run_warehouse_winners("test/one", store.path)[0]["store_name"] == "Tawreed"
    store.db.close()
    assert fetch_run_warehouse_winners("test/one", store.path)[0]["purchase_price"] == 8


def test_v5_upgrade_backfills_and_preserves_original_facts(store):
    persist(store, "Tawreed", 8)
    before = store.db.execute_query("select * from run_items")
    store.db.close()
    with sqlite3.connect(store.path) as conn:
        conn.execute("drop table run_warehouse_winners")
        conn.execute("alter table run_item_stores drop column source_label")
        conn.execute("update schema_meta set value='5' where key='schema_version'")
    OrderRunsStore._bootstrapped_paths.discard(str(store.path.resolve()))
    reopened = OrderRunsStore(store.path)
    assert fetch_run_warehouse_winners("test/one", store.path)[0]["purchase_price"] == 8
    assert reopened.db.execute_query("select * from run_items") == before
    reopened.db.close()


def test_missing_snapshots_are_explained(store):
    store.upsert_run_item("test/one", dict(item_code="001", item_name="Drug", item_qty=1))
    assert fetch_run_warehouse_winners("test/one", store.path) == []
    assert fetch_run_warehouse_exclusions("test/one", store.path)[0]["selection_reason"] == "no_eligible_offer"


def test_comparison_failure_rolls_back_item_and_offer(store, monkeypatch):
    from src.core.database import order_runs_warehouse_winners as module

    persist(store, "Tawreed", 8)
    def fail(*args):
        raise RuntimeError("comparison failed")
    monkeypatch.setattr(module, "refresh_warehouse_winner", fail)
    with pytest.raises(RuntimeError, match="comparison failed"):
        persist(store, "Tawreed", 6)
    assert fetch_run_warehouse_winners("test/one", store.path)[0]["purchase_price"] == 8
    assert store.db.execute_query("select purchase_price from run_item_stores")[0][0] == 8


def test_saved_minimum_discount_filters_excel_target_in_materialized_report(store):
    with store.db.get_connection() as conn:
        conn.execute("update runs set min_discount_pct=10 where run_key='test/one'")
        conn.commit()
    persist(store, "Tawreed below threshold", 8, discount=9)
    persist(store, "excel-target:target@Cheap.xlsx", 5, "excel_target", discount=9)
    persist(store, "excel-target:target@Eligible.xlsx", 8, "excel_target", discount=10)
    winners = fetch_run_warehouse_winners("test/one", store.path)
    assert winners[0]["store_name"] == "Eligible.xlsx"
    assert winners[0]["purchase_price"] == 7.2


def test_v8_upgrade_rebuilds_materialized_winner_using_saved_discount_floor(store):
    persist(store, "Tawreed", 8, discount=0)
    persist(store, "excel-target:target@Cheap.xlsx", 5, "excel_target", discount=9)
    persist(store, "excel-target:target@Eligible.xlsx", 8, "excel_target", discount=10)
    with store.db.get_connection() as conn:
        conn.execute("update runs set min_discount_pct=10 where run_key='test/one'")
        conn.execute(
            "update run_warehouse_winners set store_name='stale', purchase_price=5 "
            "where run_key='test/one'"
        )
        conn.execute("update schema_meta set value='8' where key='schema_version'")
        conn.commit()
    store.db.close()
    OrderRunsStore._bootstrapped_paths.discard(str(store.path.resolve()))

    reopened = OrderRunsStore(store.path)
    winners = fetch_run_warehouse_winners("test/one", store.path)
    assert winners[0]["store_name"] == "Eligible.xlsx"
    assert winners[0]["purchase_price"] == 7.2
    reopened.db.close()


def test_v9_upgrade_rebuilds_materialized_winner_with_tawreed_discount_floor(store):
    persist(store, "Tawreed below threshold", 8, discount=9)
    persist(store, "excel-target:target@Eligible.xlsx", 8, "excel_target", discount=10)
    with store.db.get_connection() as conn:
        conn.execute("update runs set min_discount_pct=10 where run_key='test/one'")
        conn.execute(
            "update run_warehouse_winners set store_name='stale', purchase_price=5 "
            "where run_key='test/one'"
        )
        conn.execute("update schema_meta set value='9' where key='schema_version'")
        conn.commit()
    store.db.close()
    OrderRunsStore._bootstrapped_paths.discard(str(store.path.resolve()))

    reopened = OrderRunsStore(store.path)
    winners = fetch_run_warehouse_winners("test/one", store.path)
    assert winners[0]["store_name"] == "Eligible.xlsx"
    assert winners[0]["purchase_price"] == 7.2
    flags = reopened.db.execute_query(
        "select source, is_winner from run_item_stores "
        "where run_key='test/one' order by source"
    )
    assert flags == [("excel_target", 1), ("store_details", 0)]
    reopened.db.close()


def test_excel_owner_retry_removes_old_catalog_offer_but_keeps_other_target(store):
    persist(store, "excel-target:target-a@old.xlsx", 6, "excel_target")
    persist(store, "excel-target:target-b@other.xlsx", 8, "excel_target")
    store.upsert_run_item(
        "test/one", {"item_code": "001", "item_name": "Drug", "item_qty": 10},
        source_kind="excel-target", source_label="target-a",
        stores=[], store_selections=[], store_source="excel_target",
        store_source_owner="target-a",
    )
    offers = store.db.execute_query(
        "select source_label from run_item_stores order by source_label"
    )
    assert offers == [("target-b@other.xlsx",)]
    assert fetch_run_warehouse_winners("test/one", store.path)[0]["purchase_price"] == 8
