"""Tests for the order-runs SQLite schema and store facade."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.database.order_runs_schema import SCHEMA_VERSION
from src.core.database.order_runs_store import OrderRunsStore


EXPECTED_TABLES = (
    "runs",
    "items",
    "stores",
    "products",
    "run_items",
    "run_item_stores",
    "run_candidates",
    "schema_meta",
)
EXPECTED_VIEWS = (
    "v_run_winners",
    "v_best_discount_per_item",
    "v_run_summary",
)


class OrderRunsSchemaTests(unittest.TestCase):
    """Validate schema creation, idempotency, and version tracking."""

    def test_schema_creates_all_tables(self) -> None:
        """Every fact, dimension, and metadata table exists after init."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            names = store.table_names()
        for expected in EXPECTED_TABLES:
            self.assertIn(expected, names)

    def test_schema_creates_all_views(self) -> None:
        """Reporting views exist so queries never re-implement the joins."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            names = store.view_names()
        for expected in EXPECTED_VIEWS:
            self.assertIn(expected, names)

    def test_schema_init_is_idempotent(self) -> None:
        """Opening the same database file twice must not raise."""
        with TemporaryDirectory() as temp:
            path = Path(temp) / "order_runs.db"
            OrderRunsStore(path)
            OrderRunsStore(path)

    def test_schema_version_is_recorded(self) -> None:
        """schema_meta stores the current schema version for future upgrades."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            self.assertEqual(store.schema_version(), SCHEMA_VERSION)

    def test_database_file_is_created_with_parent_directory(self) -> None:
        """A missing parent directory is created rather than raising."""
        with TemporaryDirectory() as temp:
            path = Path(temp) / "nested" / "dir" / "order_runs.db"
            OrderRunsStore(path)
            self.assertTrue(path.exists())

    def test_foreign_keys_are_enforced(self) -> None:
        """Fact rows cannot reference a run that does not exist."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            self.assertTrue(store.foreign_keys_enabled())

    def test_run_item_stores_has_composite_primary_key(self) -> None:
        """The composite key is what makes re-imports idempotent."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            keys = store.primary_key_columns("run_item_stores")
        self.assertEqual(keys, ["run_key", "item_key", "store_product_id"])

    def test_run_items_has_composite_primary_key(self) -> None:
        """Schema v3: one row per (run, item, source_kind, source_label)."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            keys = store.primary_key_columns("run_items")
        self.assertEqual(
            keys,
            ["run_key", "item_key", "source_kind", "source_label"],
        )

    def test_price_columns_are_explicitly_named(self) -> None:
        """The CSV artifacts swap these two names; the database must not."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            columns = store.column_names("run_item_stores")
        self.assertIn("public_price", columns)
        self.assertIn("purchase_price", columns)
        self.assertNotIn("winner_sale_price", columns)
        self.assertNotIn("winner_Purchase_Price", columns)

    def test_introspection_rejects_unsafe_table_names(self) -> None:
        """PRAGMA cannot bind parameters, so identifiers are validated."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            with self.assertRaises(ValueError):
                store.column_names("runs; drop table runs")


if __name__ == "__main__":
    unittest.main()
