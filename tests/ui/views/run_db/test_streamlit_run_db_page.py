"""Smoke tests for the Run Results (database) Streamlit tab."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_store import OrderRunsStore

SEED_DIR_ENV = "ORDER_RUNS_DB_PATH"

TAB_SCRIPT = """
import sys
sys.path.insert(0, {project_root!r})
from src.ui.views.run_db.streamlit_run_db_page import render_run_db_tab

render_run_db_tab()
"""


class RunDbTabSmokeTests(unittest.TestCase):
    """Boot the tab under Streamlit AppTest against a seeded temp database."""

    def setUp(self) -> None:
        from streamlit.testing.v1 import AppTest

        self._tmp = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp.name) / "order_runs.db"
        store = OrderRunsStore(db_path)
        self._seed(store)
        store.db.close()
        self._previous = os.environ.get(SEED_DIR_ENV)
        os.environ[SEED_DIR_ENV] = str(db_path)
        self._app_test = AppTest.from_string(
            TAB_SCRIPT.format(project_root=_project_root()),
            default_timeout=30,
        )

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop(SEED_DIR_ENV, None)
        else:
            os.environ[SEED_DIR_ENV] = self._previous
        self._tmp.cleanup()

    def _seed(self, store: OrderRunsStore) -> None:
        """Seed one finished run so the tab has data to render."""
        store.open_run(
            run_meta_row("tester", "20260101_1200", "2026-01-01T12:00:00Z")
        )
        winner = _store_row()
        store.upsert_run_item(
            "tester/20260101_1200", _summary(), stores=[_store_row(), winner],
            store_selections=[(winner, 0)],
        )
        store.finish_run("tester/20260101_1200")

    def test_tab_renders_run_selector_and_title(self) -> None:
        self._app_test.run()
        self.assertEqual(self._app_test.exception, [])
        titles = [element.value for element in self._app_test.title]
        self.assertIn("Run Results (Database)", titles)

    def test_tab_warns_when_database_missing(self) -> None:
        os.environ[SEED_DIR_ENV] = str(
            Path(self._tmp.name) / "missing" / "order_runs.db"
        )
        self._app_test.run()
        self.assertEqual(self._app_test.exception, [])
        warnings = [element.value for element in self._app_test.warning]
        self.assertTrue(
            any("order-runs database" in text for text in warnings)
        )


def _project_root() -> str:
    """Return the repository root the tests run against."""
    return str(Path(__file__).resolve().parents[4])


def _summary() -> dict:
    """Return one order summary row shaped like the live flow provides."""
    return {
        "item_code": "c1", "item_name": "ALFA", "item_qty": 1,
        "ordered_total_qty": 0, "status": "matched-only",
        "matched": 1, "manual_review_required": 0,
    }


def _store_row() -> dict:
    """Return one Tawreed-shaped offering-store row."""
    return {
        "storeProductId": "sp-a", "storeId": "s:A", "storeName": "Alpha",
        "availableQuantity": 5, "retailPrice": 10.0, "salePrice": 8.0,
        "discount": "20%",
    }


if __name__ == "__main__":
    unittest.main()

