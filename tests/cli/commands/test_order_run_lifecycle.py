"""Tests that the order runner records run start and finish around failures."""

from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from src.cli.commands import cli_order_execution as execution
from src.core.config.config_models import (
    AppConfig,
    DatabaseConfig,
    ExcelConfig,
    MatchingConfig,
    ProfileConfig,
    RuntimeConfig,
)


def _app_config(db_path: Path) -> AppConfig:
    """Return an AppConfig pointed at a temporary order-runs database."""
    return AppConfig(
        base_url="https://seller.tawreed.io/#/login",
        excel=ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
        profiles={"wardany": ProfileConfig(display_name="W", pharmacy_switch={})},
        selectors={},
        warehouse_strategy={},
        matching=MatchingConfig(),
        runtime=RuntimeConfig(),
        database=DatabaseConfig(order_runs_path=str(db_path)),
    )


def _args() -> Namespace:
    """Return the minimal CLI namespace the record wiring reads."""
    return Namespace(
        match_only=True,
        execution_mode="auto",
        matching_risk_policy="safe",
        excel="data/input/order_items/x.xlsx",
    )


class OrderRunRecordLifecycleTests(unittest.TestCase):
    """A run must be recorded as finished whether it succeeds or crashes."""

    def setUp(self) -> None:
        """Create a temporary database and artifact root."""
        self._temp = TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.db_path = self.root / "order_runs.db"
        self.config = _app_config(self.db_path)

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self._temp.cleanup()

    def _run(self, items_side_effect=None) -> None:
        """Invoke run_single_profile with the item loop stubbed out."""
        with mock.patch("src.core.artifact_run.ARTIFACT_ROOT", self.root):
            with mock.patch.object(
                execution,
                "run_single_profile_items",
                side_effect=items_side_effect,
            ):
                execution.run_single_profile(
                    self.config, "wardany", self.config.profiles["wardany"], _args()
                )

    def _runs(self) -> list:
        """Return the recorded run rows."""
        from src.core.database.order_runs_store import OrderRunsStore

        store = OrderRunsStore(self.db_path)
        return store.db.execute_query(
            "select run_key, finished_at, mode, total_items from runs"
        )

    def test_successful_run_is_opened_and_finished(self) -> None:
        """The happy path records both timestamps."""
        self._run()
        rows = self._runs()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][0].startswith("wardany/"))
        self.assertIsNotNone(rows[0][1])
        self.assertEqual(rows[0][2], "match-only")

    def test_crashed_run_is_still_marked_finished(self) -> None:
        """Without the finally block every failed run would look still-running."""
        with self.assertRaises(RuntimeError):
            self._run(items_side_effect=RuntimeError("browser died"))
        rows = self._runs()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0][1])

    def test_crash_does_not_lose_the_run_record(self) -> None:
        """The run row itself must survive so partial facts remain queryable."""
        with self.assertRaises(ValueError):
            self._run(items_side_effect=ValueError("bad excel"))
        self.assertEqual(len(self._runs()), 1)

    def test_persistence_failure_does_not_mask_the_real_error(self) -> None:
        """A database problem must not replace the exception the operator needs."""
        with mock.patch(
            "src.core.ordering.order_run_persistence._store",
            side_effect=RuntimeError("db down"),
        ):
            with self.assertRaises(ValueError):
                self._run(items_side_effect=ValueError("bad excel"))

    def test_disabled_persistence_writes_nothing(self) -> None:
        """Turning the feature off must leave no database file behind."""
        self.config = AppConfig(
            **{
                **self.config.__dict__,
                "database": DatabaseConfig(order_runs_enabled=False),
            }
        )
        self._run()
        self.assertFalse(self.db_path.exists())


if __name__ == "__main__":
    unittest.main()
