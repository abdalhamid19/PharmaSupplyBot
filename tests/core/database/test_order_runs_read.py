"""Read-side query tests for :mod:`src.core.database.order_runs_read`."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_read import (
    database_is_ready,
    fetch_item_stores,
    fetch_missed_discounts,
    fetch_run_items,
    fetch_runs,
    run_store_row_count,
)
from src.core.database.order_runs_store import OrderRunsStore

RUN_KEY = "tester/20260101_1200"


def _seed_run(store: OrderRunsStore) -> str:
    """Seed one finished run with two items, each offering two stores."""
    store.open_run(
        run_meta_row("tester", "20260101_1200", "2026-01-01T12:00:00Z", mode="match-only")
    )
    winner = _stores()[0]
    for code, name in (("c1", "ALFA"), ("c2", "BETA")):
        store.upsert_run_item(
            RUN_KEY, _summary(code, name),
            stores=_stores(), store_selections=[(winner, 0)],
        )
    store.finish_run(RUN_KEY)
    return RUN_KEY


def _summary(code: str, name: str) -> dict:
    """Return one order summary row shaped like the live flow provides."""
    return {
        "item_code": code, "item_name": name, "item_qty": 1,
        "ordered_total_qty": 0, "status": "matched-only",
        "matched": 1, "manual_review_required": 0,
    }


def _stores() -> list[dict]:
    """Return two offering stores; the winner has the weaker discount."""
    return [
        {
            "storeProductId": "sp-a", "storeId": "s:A", "storeName": "Alpha",
            "availableQuantity": 5, "retailPrice": 10.0, "salePrice": 8.0,
            "discount": "20%",
        },
        {
            "storeProductId": "sp-b", "storeId": "s:B", "storeName": "Beta",
            "availableQuantity": 9, "retailPrice": 10.0, "salePrice": 7.0,
            "discount": "30%",
        },
    ]
class OrderRunsReadTests(unittest.TestCase):
    """End-to-end read queries against a freshly bootstrapped temp DB."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = OrderRunsStore(Path(self._tmp.name) / "runs.db")
        self.run_key = _seed_run(self.store)

    def tearDown(self) -> None:
        self.store.db.close()
        self._tmp.cleanup()

    def test_database_is_ready_after_bootstrap(self) -> None:
        self.assertTrue(database_is_ready(self.store.db.path))

    def test_fetch_runs_returns_aggregates(self) -> None:
        runs = fetch_runs(db=self.store.db.path)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["items"], 2)
        self.assertEqual(runs[0]["matched"], 2)

    def test_fetch_run_items_joins_item_dimension(self) -> None:
        items = fetch_run_items(RUN_KEY, db=self.store.db.path)
        names = {item["item_name"] for item in items}
        self.assertEqual(names, {"ALFA", "BETA"})

    def test_fetch_item_stores_orders_winner_first(self) -> None:
        stores = fetch_item_stores(RUN_KEY, "C1::ALFA", db=self.store.db.path)
        self.assertEqual(len(stores), 2)
        self.assertEqual(stores[0]["is_winner"], 1)
        self.assertEqual(stores[0]["store_name"], "Alpha")

    def test_missed_discounts_flags_beaten_winner(self) -> None:
        rows = fetch_missed_discounts(RUN_KEY, db=self.store.db.path)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0]["missed"], 10.0)
        self.assertAlmostEqual(rows[0]["best_discount"], 30.0)

    def test_run_store_row_count(self) -> None:
        self.assertEqual(run_store_row_count(RUN_KEY, db=self.store.db.path), 4)


if __name__ == "__main__":
    unittest.main()
