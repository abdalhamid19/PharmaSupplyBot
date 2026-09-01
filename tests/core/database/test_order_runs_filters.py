"""Tests for the KPI-card drilldown filter read functions.

Each test seeds one run with items spanning every filter category so the
returned rows can be asserted against a known shape.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_read_filters import (
    fetch_run_items_flagged,
    fetch_run_items_matched,
    fetch_run_items_not_orderable,
    fetch_run_items_ordered,
)
from src.core.database.order_runs_read_sql import QUERY_COLUMNS
from src.core.database.order_runs_store import OrderRunsStore

RUN_KEY = "tester/20260201_0900"
_EXPECTED_COLUMNS = set(QUERY_COLUMNS["items"])


def _summary(code: str, name: str, **overrides) -> dict:
    """Return one order-item summary shaped like the live flow provides."""
    row = {
        "item_code": code,
        "item_name": name,
        "item_qty": 1,
        "ordered_total_qty": 0,
        "status": "matched-only",
        "matched": 1,
        "manual_review_required": 0,
    }
    row.update(overrides)
    return row


def _seed_run(store: OrderRunsStore) -> str:
    """Seed one run with four items, one per KPI-drilldown category."""
    store.open_run(
        run_meta_row("tester", "20260201_0900", started_at="2026-02-01T09:00:00Z")
    )
    store.upsert_run_item(RUN_KEY, _summary("M1", "MATCHED"))
    store.upsert_run_item(
        RUN_KEY,
        _summary(
            "F1", "FLAGGED", manual_review_required=1, reason="manual review needed"
        ),
    )
    store.upsert_run_item(
        RUN_KEY,
        _summary(
            "N1",
            "NOT-ORDERABLE",
            status="not-orderable",
            matched=0,
            reason="out of stock",
        ),
    )
    store.upsert_run_item(
        RUN_KEY,
        _summary(
            "O1",
            "ORDERED",
            status="added-to-cart",
            ordered_total_qty=5,
            reason="added to cart",
        ),
    )
    return RUN_KEY


class OrderRunsFiltersTests(unittest.TestCase):
    """Verify each KPI-drilldown query against a freshly bootstrapped DB."""

    def setUp(self) -> None:
        """Create an isolated database seeded with one item per category."""
        self._tmp = tempfile.TemporaryDirectory()
        self.store = OrderRunsStore(Path(self._tmp.name) / "runs.db")
        self.run_key = _seed_run(self.store)

    def tearDown(self) -> None:
        """Remove the temporary database directory."""
        self.store.db.close()
        self._tmp.cleanup()

    def test_fetch_run_items_matched_excludes_not_orderable(self) -> None:
        """Matched items must include flag/ordered rows but skip not-orderable."""
        rows = fetch_run_items_matched(RUN_KEY, db=self.store.db.path)
        names = {row["item_name"] for row in rows}
        self.assertEqual(len(rows), 3)
        self.assertEqual(names, {"MATCHED", "FLAGGED", "ORDERED"})
        for row in rows:
            self.assertEqual(row["matched"], 1)
            self.assertNotEqual(row["status"], "not-orderable")
            self.assertEqual(set(row.keys()), _EXPECTED_COLUMNS)

    def test_fetch_run_items_flagged_returns_only_flagged(self) -> None:
        """Flagged items must equal rows with manual_review_required = 1."""
        rows = fetch_run_items_flagged(RUN_KEY, db=self.store.db.path)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["item_name"], "FLAGGED")
        self.assertEqual(row["item_code"], "F1")
        self.assertEqual(row["manual_review_required"], 1)
        self.assertEqual(row["status"], "matched-only")

    def test_fetch_run_items_not_orderable_returns_only_that_status(self) -> None:
        """Not-orderable items must equal rows with status = 'not-orderable'."""
        rows = fetch_run_items_not_orderable(RUN_KEY, db=self.store.db.path)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["item_name"], "NOT-ORDERABLE")
        self.assertEqual(row["item_code"], "N1")
        self.assertEqual(row["status"], "not-orderable")
        self.assertEqual(row["matched"], 0)

    def test_fetch_run_items_ordered_returns_only_positive_qty(self) -> None:
        """Ordered items must equal rows where ordered_qty > 0."""
        rows = fetch_run_items_ordered(RUN_KEY, db=self.store.db.path)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["item_name"], "ORDERED")
        self.assertEqual(row["item_code"], "O1")
        self.assertGreater(row["ordered_qty"], 0)


if __name__ == "__main__":
    unittest.main()