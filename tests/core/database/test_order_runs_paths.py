"""Tests for order-runs database path resolution and isolation."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from src.core.database.database_credentials import _DEFAULT_DB_PATH
from src.core.database.order_runs_paths import (
    DEFAULT_ORDER_RUNS_DB,
    ORDER_RUNS_PATH_ENV,
    default_order_runs_db,
)
from src.core.database.order_runs_store import OrderRunsStore


class OrderRunsPathTests(unittest.TestCase):
    """Validate the order-runs database stays separate from manual review."""

    def test_default_path_is_not_the_manual_review_database(self) -> None:
        """Sharing one file would couple vacuuming and durability settings."""
        self.assertNotEqual(DEFAULT_ORDER_RUNS_DB, _DEFAULT_DB_PATH)

    def test_default_path_lives_under_state(self) -> None:
        """state/ is gitignored, so the database is never committed."""
        self.assertEqual(DEFAULT_ORDER_RUNS_DB.parent.name, "state")
        self.assertEqual(DEFAULT_ORDER_RUNS_DB.name, "order_runs.db")

    def test_env_variable_overrides_default(self) -> None:
        """Tests and side-by-side runs can redirect the database file."""
        with TemporaryDirectory() as temp:
            target = Path(temp) / "custom.db"
            with mock.patch.dict(os.environ, {ORDER_RUNS_PATH_ENV: str(target)}):
                self.assertEqual(default_order_runs_db(), target)

    def test_relative_env_path_resolves_against_project_root(self) -> None:
        """Subprocess workers must agree regardless of working directory."""
        with mock.patch.dict(os.environ, {ORDER_RUNS_PATH_ENV: "state/other.db"}):
            resolved = default_order_runs_db()
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved.name, "other.db")

    def test_separate_paths_produce_independent_databases(self) -> None:
        """Two store instances on different files never share tables."""
        with TemporaryDirectory() as temp:
            first = OrderRunsStore(Path(temp) / "a.db")
            second = OrderRunsStore(Path(temp) / "b.db")
            first.db.execute_update(
                "insert into runs (run_key, run_id, profile_key, started_at)"
                " values ('p/1', '1', 'p', '2026-01-01T00:00:00')"
            )
            rows = second.db.execute_query("select count(*) from runs")
        self.assertEqual(int(rows[0][0]), 0)

    def test_manual_review_schema_is_not_created(self) -> None:
        """The order-runs bootstrap must not touch the manual-review table."""
        with TemporaryDirectory() as temp:
            store = OrderRunsStore(Path(temp) / "order_runs.db")
            self.assertNotIn("manual_review_decisions", store.table_names())


if __name__ == "__main__":
    unittest.main()
