"""Behavioural tests for order-runs schema constraints and views."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.database.order_runs_store import OrderRunsStore

_NOW = "2026-08-30T18:09:00"


def _seed(store: OrderRunsStore) -> None:
    """Insert one run with one item, one product, one store, and one snapshot."""
    with store.db.get_connection() as conn:
        conn.execute(
            "insert into runs (run_key, run_id, profile_key, started_at, mode)"
            " values ('wardany/20260830_1809', '20260830_1809', 'wardany', ?, 'order')",
            (_NOW,),
        )
        conn.execute(
            "insert into items (item_key, item_code, item_name,"
            " first_seen_at, last_seen_at) values ('12345::CAL MAG', '12345',"
            " 'CAL MAG', ?, ?)",
            (_NOW, _NOW),
        )
        conn.execute(
            "insert into stores (store_key, store_name, first_seen_at, last_seen_at)"
            " values ('storeId:55', 'شركه العاصمه', ?, ?)",
            (_NOW, _NOW),
        )
        conn.execute(
            "insert into products (store_product_id, product_id, name_ar, name_en,"
            " first_seen_at, last_seen_at) values ('2902379', '2505', 'كال ماج',"
            " 'CAL MAG 30 F.C. TABLETS', ?, ?)",
            (_NOW, _NOW),
        )
        conn.execute(
            "insert into run_items (run_key, item_key, requested_qty, ordered_qty,"
            " status, matched, winner_store_product_id, winner_store_key)"
            " values ('wardany/20260830_1809', '12345::CAL MAG', 10, 10,"
            " 'added-to-cart', 1, '2902379', 'storeId:55')"
        )
        conn.execute(
            "insert into run_item_stores (run_key, item_key, store_product_id,"
            " store_key, available_qty, public_price, purchase_price,"
            " discount_percent, currency, is_winner, ordered_qty,"
            " rank_by_discount, source, captured_at) values"
            " ('wardany/20260830_1809', '12345::CAL MAG', '2902379', 'storeId:55',"
            " 22, 147.0, 116.13, 21.0, 'ج.م', 1, 10, 1, 'store_details', ?)",
            (_NOW,),
        )
        conn.commit()


class OrderRunsSchemaBehaviourTests(unittest.TestCase):
    """Validate keys, cascades, and view output on real rows."""

    def test_duplicate_run_item_is_rejected_without_upsert(self) -> None:
        """The composite key is what later makes UPSERT-based re-imports safe."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            with self.assertRaises(sqlite3.IntegrityError):
                store.db.execute_update(
                    "insert into run_items (run_key, item_key) values"
                    " ('wardany/20260830_1809', '12345::CAL MAG')"
                )

    def test_orphan_run_item_is_rejected(self) -> None:
        """Facts cannot reference a run that was never opened."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            with self.assertRaises(sqlite3.IntegrityError):
                store.db.execute_update(
                    "insert into run_items (run_key, item_key) values"
                    " ('missing/run', '12345::CAL MAG')"
                )

    def test_deleting_a_run_cascades_to_its_facts(self) -> None:
        """Retention cleanup is a single DELETE on runs."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            store.db.execute_update(
                "delete from runs where run_key = 'wardany/20260830_1809'"
            )
            items = store.db.execute_query("select count(*) from run_items")
            snapshots = store.db.execute_query("select count(*) from run_item_stores")
        self.assertEqual(int(items[0][0]), 0)
        self.assertEqual(int(snapshots[0][0]), 0)

    def test_run_winners_view_flattens_the_winning_store(self) -> None:
        """v_run_winners is the shape the UI and queries consume."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            rows = store.db.execute_query(
                "select item_code, store_name, public_price, purchase_price,"
                " discount_percent from v_run_winners"
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "12345")
        self.assertEqual(rows[0][1], "شركه العاصمه")
        self.assertAlmostEqual(float(rows[0][2]), 147.0)
        self.assertAlmostEqual(float(rows[0][3]), 116.13)
        self.assertAlmostEqual(float(rows[0][4]), 21.0)

    def test_run_summary_view_counts_statuses(self) -> None:
        """v_run_summary replaces reading the summary CSV to count outcomes."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            rows = store.db.execute_query(
                "select items, matched, added_to_cart, total_ordered from v_run_summary"
            )
        self.assertEqual(tuple(int(value) for value in rows[0]), (1, 1, 1, 10))

    def test_run_summary_view_excludes_not_orderable_from_matched(self) -> None:
        """Catalog matches that cannot be ordered are not 'matched' outcomes."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            with store.db.get_connection() as conn:
                conn.execute(
                    "insert into items (item_key, item_code, item_name,"
                    " first_seen_at, last_seen_at) values ('6789::HAEMOJET',"
                    " '6789', 'HAEMOJET AMP', ?, ?)",
                    (_NOW, _NOW),
                )
                conn.execute(
                    "insert into run_items (run_key, item_key, requested_qty,"
                    " ordered_qty, status, matched)"
                    " values ('wardany/20260830_1809', '6789::HAEMOJET', 1, 0,"
                    " 'not-orderable', 1)"
                )
                conn.commit()
            rows = store.db.execute_query(
                "select items, matched from v_run_summary"
            )
        self.assertEqual(tuple(int(value) for value in rows[0]), (2, 1))

    def test_bootstrap_recreates_stale_views_from_older_schema(self) -> None:
        """A v1 database must get the v4 view definition on first open."""
        with TemporaryDirectory() as temp:
            path = Path(temp) / "order_runs.db"
            store = OrderRunsStore(path)
            _seed(store)
            with store.db.get_connection() as conn:
                conn.execute("drop view v_run_summary")
                conn.execute(
                    "create view v_run_summary as"
                    " select run_key, sum(ri.matched) as matched"
                    " from run_items ri group by run_key"
                )
                conn.execute(
                    "update schema_meta set value = '1'"
                    " where key = 'schema_version'"
                )
                conn.commit()
            store.db.close()
            OrderRunsStore._bootstrapped_paths.clear()
            reopened = OrderRunsStore(path)
            columns = reopened.column_names("v_run_summary")
            version = reopened.schema_version()
            reopened.db.close()
        self.assertIn("added_to_cart", columns)
        self.assertEqual(version, 4)

    def test_best_discount_view_uses_precomputed_rank(self) -> None:
        """rank_by_discount avoids a window function in every query."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            rows = store.db.execute_query(
                "select store_key, discount_percent from v_best_discount_per_item"
            )
        self.assertEqual(rows[0][0], "storeId:55")

    def test_purchase_price_is_lower_than_public_price(self) -> None:
        """Guards against re-introducing the swapped CSV price naming."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            _seed(store)
            rows = store.db.execute_query(
                "select public_price, purchase_price, discount_percent"
                " from run_item_stores"
            )
        public, purchase, discount = (float(value) for value in rows[0])
        self.assertLess(purchase, public)
        self.assertAlmostEqual((public - purchase) / public * 100, discount, places=1)


if __name__ == "__main__":
    unittest.main()
