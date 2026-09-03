"""Tests for persisting per-item offering-store snapshots."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_store import OrderRunsStore

_NOW = "2026-08-30T18:09:00"
_LATER = "2026-08-30T18:14:00"
_RUN = "wardany/20260830_1809"
_ITEM = "12345::CAL MAG"


def _store_row(store_id: int, discount: float, qty: int = 10) -> dict:
    """Return a Tawreed store-details row shaped like the real payload."""
    return {
        "storeId": store_id,
        "storeName": f"شركه {store_id}",
        "storeProductId": 2900000 + store_id,
        "productId": 2505,
        "productName": "كال ماج 30 اقراص",
        "productNameEn": "CAL MAG 30 F.C. TABLETS",
        "availableQuantity": qty,
        "retailPrice": 147.0,
        "salePrice": round(147.0 * (1 - discount / 100), 2),
        "discountPercent": discount,
        "currency": "ج.م",
    }


def _summary(**overrides) -> dict:
    """Return a minimal order_item_summary-shaped row."""
    row = {
        "item_code": "12345",
        "item_name": "CAL MAG",
        "item_qty": 10,
        "ordered_total_qty": 10,
        "status": "added-to-cart",
        "matched": True,
    }
    row.update(overrides)
    return row


class StoreSnapshotPersistenceTests(unittest.TestCase):
    """All offering stores land in the database with their dimensions."""

    def setUp(self) -> None:
        """Open an isolated database with one run already recorded."""
        self._temp = TemporaryDirectory()
        self.store = OrderRunsStore(Path(self._temp.name) / "order_runs.db")
        self.store.open_run(
            run_meta_row("wardany", "20260830_1809", started_at=_NOW)
        )

    def tearDown(self) -> None:
        """Remove the temporary database."""
        self._temp.cleanup()

    def _persist(self, stores, selections=None, now=_NOW, source="store_details"):
        """Persist one item with its store snapshot."""
        self.store.upsert_run_item(
            _RUN,
            _summary(),
            now=now,
            stores=stores,
            store_selections=selections or [],
            store_source=source,
        )

    def test_all_offering_stores_are_stored(self) -> None:
        """The feature's core promise: not just the winner."""
        self._persist([_store_row(1, 21.0), _store_row(2, 15.0), _store_row(3, 8.0)])
        self.assertEqual(self.store.count_run_item_stores(_RUN, _ITEM), 3)

    def test_store_and_product_dimensions_are_created(self) -> None:
        """Facts reference dimensions, so those must exist first."""
        self._persist([_store_row(1, 21.0), _store_row(2, 15.0)])
        stores = self.store.db.execute_query("select store_key from stores")
        products = self.store.db.execute_query("select store_product_id from products")
        self.assertEqual(sorted(r[0] for r in stores), ["storeId:1", "storeId:2"])
        self.assertEqual(sorted(r[0] for r in products), ["2900001", "2900002"])

    def test_stores_offering_count_lands_on_the_item_fact(self) -> None:
        """run_items carries the count so summaries need no extra join."""
        self._persist([_store_row(1, 21.0), _store_row(2, 15.0)])
        rows = self.store.db.execute_query(
            "select stores_offering from run_items where item_key = ?", (_ITEM,)
        )
        self.assertEqual(int(rows[0][0]), 2)

    def test_winner_store_key_is_denormalised_onto_run_items(self) -> None:
        """Lets the run summary resolve the winner without scanning snapshots."""
        stores = [_store_row(1, 8.0), _store_row(2, 21.0)]
        self._persist(stores, selections=[(stores[1], 10)])
        rows = self.store.db.execute_query(
            "select winner_store_key, winner_store_product_id from run_items"
        )
        self.assertEqual(rows[0][0], "storeId:2")
        self.assertEqual(rows[0][1], "2900002")

    def test_exactly_one_winner_row_per_item(self) -> None:
        """Enforced by the writer, relied on by v_run_winners."""
        stores = [_store_row(1, 21.0), _store_row(2, 15.0)]
        self._persist(stores, selections=[(stores[0], 6), (stores[1], 4)])
        rows = self.store.db.execute_query(
            "select count(*) from run_item_stores where run_key=? and is_winner=1",
            (_RUN,),
        )
        self.assertEqual(int(rows[0][0]), 1)

    def test_rewriting_an_item_replaces_its_snapshot(self) -> None:
        """A retry with fewer stores must not leave stale rows behind."""
        self._persist([_store_row(1, 21.0), _store_row(2, 15.0), _store_row(3, 8.0)])
        self._persist([_store_row(1, 21.0)], now=_LATER)
        self.assertEqual(self.store.count_run_item_stores(_RUN, _ITEM), 1)

    def test_repersisting_identical_data_is_idempotent(self) -> None:
        """Direct writes plus a later db-import must not duplicate rows."""
        stores = [_store_row(1, 21.0), _store_row(2, 15.0)]
        self._persist(stores)
        self._persist(stores, now=_LATER)
        self.assertEqual(self.store.count_run_item_stores(_RUN, _ITEM), 2)

    def test_dimension_first_seen_at_survives_rewrites(self) -> None:
        """Store discovery date is a historical fact."""
        self._persist([_store_row(1, 21.0)])
        self._persist([_store_row(1, 21.0)], now=_LATER)
        rows = self.store.db.execute_query(
            "select first_seen_at, last_seen_at from stores"
        )
        self.assertEqual(rows[0][0], _NOW)
        self.assertEqual(rows[0][1], _LATER)

    def test_item_without_stores_writes_no_snapshot_rows(self) -> None:
        """A no-results item has nothing to snapshot."""
        self.store.upsert_run_item(
            _RUN, _summary(status="no-results", matched=False), now=_NOW
        )
        self.assertEqual(self.store.count_run_item_stores(_RUN, _ITEM), 0)

    def test_best_discount_view_returns_the_top_store(self) -> None:
        """The precomputed rank is what makes this a single index lookup."""
        self._persist([_store_row(1, 8.0), _store_row(2, 21.0), _store_row(3, 15.0)])
        rows = self.store.db.execute_query(
            "select store_key, discount_percent from v_best_discount_per_item"
            " where run_key = ?",
            (_RUN,),
        )
        self.assertEqual(rows[0][0], "storeId:2")

    def test_run_winners_view_joins_names_and_prices(self) -> None:
        """This view is the intended read path for the UI."""
        stores = [_store_row(1, 21.0)]
        self._persist(stores, selections=[(stores[0], 10)])
        rows = self.store.db.execute_query(
            "select item_code, store_name, name_en, public_price, purchase_price"
            " from v_run_winners where run_key = ?",
            (_RUN,),
        )
        self.assertEqual(rows[0][0], "12345")
        self.assertEqual(rows[0][1], "شركه 1")
        self.assertEqual(rows[0][2], "CAL MAG 30 F.C. TABLETS")
        self.assertAlmostEqual(float(rows[0][3]), 147.0)
        self.assertAlmostEqual(float(rows[0][4]), 116.13)

    def test_suboptimal_choice_is_detectable(self) -> None:
        """The question the old CSV output could never answer."""
        stores = [_store_row(1, 8.0), _store_row(2, 21.0)]
        self._persist(stores, selections=[(stores[0], 10)])
        rows = self.store.db.execute_query(
            "select w.discount_percent, b.discount_percent from run_item_stores w"
            " join run_item_stores b on b.run_key = w.run_key"
            " and b.item_key = w.item_key and b.rank_by_discount = 1"
            " where w.run_key = ? and w.is_winner = 1",
            (_RUN,),
        )
        chosen, best = float(rows[0][0]), float(rows[0][1])
        self.assertAlmostEqual(chosen, 8.0)
        self.assertAlmostEqual(best, 21.0)
        self.assertGreater(best, chosen)

    def test_deleting_the_run_cascades_to_snapshots(self) -> None:
        """Retention cleanup stays a single DELETE on runs."""
        self._persist([_store_row(1, 21.0), _store_row(2, 15.0)])
        self.store.db.execute_update("delete from runs where run_key = ?", (_RUN,))
        rows = self.store.db.execute_query("select count(*) from run_item_stores")
        self.assertEqual(int(rows[0][0]), 0)


if __name__ == "__main__":
    unittest.main()
