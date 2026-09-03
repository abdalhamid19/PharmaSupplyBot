"""Tests for writing runs, items, and run items to the order-runs database."""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_rows import run_item_row
from src.core.database.order_runs_store import OrderRunsStore

_STARTED = "2026-08-30T18:09:00"
_FINISHED = "2026-08-30T18:14:00"
_RUN_KEY = "wardany/20260830_1809"


def _summary(code: str = "12345", name: str = "CAL MAG", **overrides):
    """Return a minimal order_item_summary-shaped row."""
    row = {
        "item_code": code,
        "item_name": name,
        "item_qty": 10,
        "ordered_total_qty": 10,
        "status": "added-to-cart",
        "reason": "Added to cart.",
        "matched": True,
        "manual_review_required": False,
        "matched_query": "CAL MAG 30",
        "deterministic_score": 24.5,
        "winner_store_product_id": "2902379",
    }
    row.update(overrides)
    return row


class OrderRunsWriterTests(unittest.TestCase):
    """Validate run lifecycle writes and idempotency."""

    def setUp(self) -> None:
        """Create an isolated database for each test."""
        self._temp = TemporaryDirectory()
        self.store = OrderRunsStore(Path(self._temp.name) / "order_runs.db")
        self.meta = run_meta_row("wardany", "20260830_1809", started_at=_STARTED)

    def tearDown(self) -> None:
        """Remove the temporary database directory."""
        self._temp.cleanup()

    def test_open_run_inserts_one_row(self) -> None:
        """The run record must exist before any fact row references it."""
        self.store.open_run(self.meta)
        rows = self.store.db.execute_query("select run_key, finished_at from runs")
        self.assertEqual(rows[0][0], _RUN_KEY)
        self.assertIsNone(rows[0][1])

    def test_open_run_twice_keeps_one_row(self) -> None:
        """A retried or re-imported run must not duplicate its record."""
        self.store.open_run(self.meta)
        self.store.open_run(self.meta)
        rows = self.store.db.execute_query("select count(*) from runs")
        self.assertEqual(int(rows[0][0]), 1)

    def test_open_run_updates_changed_options(self) -> None:
        """Re-opening with new options corrects the record rather than ignoring it."""
        self.store.open_run(self.meta)
        changed = run_meta_row(
            "wardany", "20260830_1809", started_at=_STARTED, warehouse_mode="max_discount"
        )
        self.store.open_run(changed)
        rows = self.store.db.execute_query("select warehouse_mode from runs")
        self.assertEqual(rows[0][0], "max_discount")

    def test_upsert_run_item_creates_item_dimension(self) -> None:
        """Writing a fact must auto-create its dimension row."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        rows = self.store.db.execute_query(
            "select item_key, item_code, item_name, first_seen_at from items"
        )
        self.assertEqual(rows[0][0], "12345::CAL MAG")
        self.assertEqual(rows[0][1], "12345")
        self.assertEqual(rows[0][2], "CAL MAG")
        self.assertEqual(rows[0][3], _STARTED)

    def test_upsert_run_item_writes_the_fact_row(self) -> None:
        """The fact row carries the run outcome for later comparison."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        rows = self.store.db.execute_query(
            "select requested_qty, ordered_qty, status, matched,"
            " winner_store_product_id from run_items"
        )
        self.assertEqual(tuple(rows[0]), (10, 10, "added-to-cart", 1, "2902379"))

    def test_upsert_run_item_twice_keeps_one_row(self) -> None:
        """Direct writes plus a later db-import must not double-count items."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_FINISHED)
        self.assertEqual(self.store.count_run_items(_RUN_KEY), 1)

    def test_upsert_run_item_updates_status_on_rewrite(self) -> None:
        """A corrected re-import overwrites the stale outcome."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(status="no-results"), now=_STARTED)
        self.store.upsert_run_item(_RUN_KEY, _summary(status="added-to-cart"), now=_FINISHED)
        rows = self.store.db.execute_query("select status from run_items")
        self.assertEqual(rows[0][0], "added-to-cart")

    def test_rewrite_preserves_first_seen_at(self) -> None:
        """first_seen_at is a historical fact and must never move forward."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_FINISHED)
        rows = self.store.db.execute_query(
            "select first_seen_at, last_seen_at from items"
        )
        self.assertEqual(rows[0][0], _STARTED)
        self.assertEqual(rows[0][1], _FINISHED)

    def test_empty_item_name_does_not_erase_stored_name(self) -> None:
        """A blank value in one run must not wipe a good value from another."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        self.store.upsert_run_item(
            _RUN_KEY, _summary(name="CAL MAG", code=""), now=_FINISHED
        )
        rows = self.store.db.execute_query("select item_code from items")
        self.assertEqual(rows[0][0], "12345")

    def test_finish_run_sets_timestamp_and_total(self) -> None:
        """total_items is derived from the facts, not from a caller's counter."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary("1", "A"), now=_STARTED)
        self.store.upsert_run_item(_RUN_KEY, _summary("2", "B"), now=_STARTED)
        self.store.finish_run(_RUN_KEY, finished_at=_FINISHED)
        rows = self.store.db.execute_query(
            "select finished_at, total_items from runs"
        )
        self.assertEqual(rows[0][0], _FINISHED)
        self.assertEqual(int(rows[0][1]), 2)

    def test_finish_run_on_unknown_run_is_a_no_op(self) -> None:
        """A crashed run may never have been opened; this must not raise."""
        self.store.finish_run("missing/run", finished_at=_FINISHED)

    def test_run_exists_reports_open_runs(self) -> None:
        """Used by db-import to decide between insert and update paths."""
        self.assertFalse(self.store.run_exists(_RUN_KEY))
        self.store.open_run(self.meta)
        self.assertTrue(self.store.run_exists(_RUN_KEY))

    def test_item_without_open_run_is_rejected(self) -> None:
        """Foreign keys stop orphan facts from accumulating silently."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)

    def test_two_items_share_one_dimension_row(self) -> None:
        """The same item across runs must not fork the dimension."""
        self.store.open_run(self.meta)
        second = run_meta_row("wardany", "20260830_1810", started_at=_FINISHED)
        self.store.open_run(second)
        self.store.upsert_run_item(_RUN_KEY, _summary(), now=_STARTED)
        self.store.upsert_run_item(second["run_key"], _summary(), now=_FINISHED)
        rows = self.store.db.execute_query("select count(*) from items")
        self.assertEqual(int(rows[0][0]), 1)

    def test_run_summary_view_reflects_written_rows(self) -> None:
        """The reporting view is the intended read path for the UI."""
        self.store.open_run(self.meta)
        self.store.upsert_run_item(_RUN_KEY, _summary("1", "A"), now=_STARTED)
        self.store.upsert_run_item(
            _RUN_KEY,
            _summary("2", "B", status="no-results", matched=False, ordered_total_qty=0),
            now=_STARTED,
        )
        rows = self.store.db.execute_query(
            "select items, matched, no_results, total_ordered from v_run_summary"
        )
        self.assertEqual(tuple(int(value) for value in rows[0]), (2, 1, 1, 10))

    def test_row_builders_are_shared_with_direct_sql_path(self) -> None:
        """upsert_run_item must write exactly what run_item_row produces."""
        self.store.open_run(self.meta)
        summary = _summary()
        self.store.upsert_run_item(_RUN_KEY, summary, now=_STARTED)
        expected = run_item_row(_RUN_KEY, summary)
        rows = self.store.db.execute_query(
            "select matched_query, deterministic_score from run_items"
        )
        self.assertEqual(rows[0][0], expected["matched_query"])
        self.assertAlmostEqual(float(rows[0][1]), float(expected["deterministic_score"]))


if __name__ == "__main__":
    unittest.main()
