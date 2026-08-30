"""Tests that order-run persistence can never break an order run."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from src.core.ordering import order_run_persistence as persistence


class PersistenceGateTests(unittest.TestCase):
    """Persistence is opt-out and must cost nothing when disabled."""

    def test_disabled_config_blocks_all_writes(self) -> None:
        """An operator turns persistence off without editing code."""
        options = {"enabled": False}
        self.assertFalse(persistence.persistence_enabled(options))
        with mock.patch.object(persistence, "_store") as store:
            self.assertIsNone(
                persistence.open_run_record("wardany", "1", {}, options)
            )
            persistence.record_run_item("wardany/1", {"item_code": "1"}, options)
            persistence.finish_run_record("wardany/1", options)
        store.assert_not_called()

    def test_enabled_by_default(self) -> None:
        """Absent configuration keeps persistence on."""
        self.assertTrue(persistence.persistence_enabled({}))
        self.assertTrue(persistence.persistence_enabled(None))

    def test_blank_configured_path_disables_persistence(self) -> None:
        """An empty path is an explicit off switch, not a fallback to default."""
        self.assertFalse(persistence.persistence_enabled({"path": ""}))


class PersistenceFailureIsolationTests(unittest.TestCase):
    """A database error must be logged and swallowed, never propagated.

    The warning is asserted by patching ``logger.warning`` rather than with
    ``assertLogs`` because ``tools/run_unit_tests.py`` calls
    ``logging.disable(CRITICAL)``, which would make ``assertLogs`` capture
    nothing and fail spuriously.
    """

    def _failing_store(self):
        """Return a patch context where the store constructor raises."""
        return mock.patch.object(persistence, "_store", side_effect=RuntimeError("boom"))

    def test_open_run_swallows_store_errors(self) -> None:
        """A failure here would abort the run before a single item is processed."""
        with self._failing_store(), mock.patch.object(
            persistence.logger, "warning"
        ) as warn:
            result = persistence.open_run_record("wardany", "20260830_1809", {}, {})
        self.assertIsNone(result)
        warn.assert_called_once()

    def test_record_item_swallows_store_errors(self) -> None:
        """Losing one analytics row must not lose a real cart addition."""
        with self._failing_store(), mock.patch.object(
            persistence.logger, "warning"
        ) as warn:
            persistence.record_run_item("wardany/1", {"item_code": "1"}, {})
        warn.assert_called_once()

    def test_finish_run_swallows_store_errors(self) -> None:
        """A crashed run must still exit cleanly."""
        with self._failing_store(), mock.patch.object(
            persistence.logger, "warning"
        ) as warn:
            persistence.finish_run_record("wardany/1", {})
        warn.assert_called_once()

    def test_logged_warning_names_the_item(self) -> None:
        """Silent loss is unacceptable; the log must identify what was dropped."""
        with self._failing_store(), mock.patch.object(
            persistence.logger, "warning"
        ) as warn:
            persistence.record_run_item("wardany/1", {"item_code": "12345"}, {})
        self.assertIn("12345", str(warn.call_args))

    def test_logged_warning_includes_the_traceback(self) -> None:
        """Without exc_info the operator cannot diagnose the failure."""
        with self._failing_store(), mock.patch.object(
            persistence.logger, "warning"
        ) as warn:
            persistence.record_run_item("wardany/1", {"item_code": "1"}, {})
        self.assertTrue(warn.call_args.kwargs.get("exc_info"))

    def test_record_item_is_a_no_op_without_run_key(self) -> None:
        """When open_run failed there is no run to attach facts to."""
        with mock.patch.object(persistence, "_store") as store:
            persistence.record_run_item("", {"item_code": "1"}, {})
        store.assert_not_called()


class PersistenceHappyPathTests(unittest.TestCase):
    """The full lifecycle writes to a real database file."""

    def test_open_record_finish_writes_expected_rows(self) -> None:
        """End-to-end check against a temporary database."""
        with TemporaryDirectory() as temp:
            path = Path(temp) / "order_runs.db"
            options = {"enabled": True, "path": path}
            run_key = persistence.open_run_record(
                "wardany", "20260830_1809", {"mode": "match-only"}, options
            )
            self.assertEqual(run_key, "wardany/20260830_1809")
            persistence.record_run_item(
                run_key,
                {
                    "item_code": "12345",
                    "item_name": "CAL MAG",
                    "item_qty": 10,
                    "status": "matched-only",
                    "matched": True,
                },
                options,
            )
            persistence.finish_run_record(run_key, options)

            from src.core.database.order_runs_store import OrderRunsStore

            store = OrderRunsStore(path)
            rows = store.db.execute_query(
                "select items, matched from v_run_summary where run_key = ?",
                (run_key,),
            )
            finished = store.db.execute_query(
                "select finished_at, total_items from runs where run_key = ?",
                (run_key,),
            )
        self.assertEqual(tuple(int(value) for value in rows[0]), (1, 1))
        self.assertIsNotNone(finished[0][0])
        self.assertEqual(int(finished[0][1]), 1)


if __name__ == "__main__":
    unittest.main()
