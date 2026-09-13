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
        """Seed one finished run with a real basket addition."""
        store.open_run(
            run_meta_row("tester", "20260101_1200", "2026-01-01T12:00:00Z")
        )
        selected = _store_row()
        store.upsert_run_item(
            "tester/20260101_1200", _summary(),
            source_kind="tawreed", source_label="tester",
            store_source="store_details",
            stores=[selected], store_selections=[(selected, 1)],
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
        self.assertTrue(any("order-runs database" in text for text in warnings))

    def test_actual_basket_groups_items_before_existing_diagnostics(self) -> None:
        self._app_test.run()
        self.assertEqual(self._app_test.exception, [])
        headings = [element.value for element in self._app_test.subheader]
        self.assertIn("نتيجة الشراء الفعلية", headings)
        download_labels = [element.label for element in self._app_test.download_button]
        self.assertIn("تحميل ملفات Excel مستقلة لكل فرع (ZIP)", download_labels)

    def test_match_only_run_shows_hypothetical_warehouse_groups(self) -> None:
        db_path = Path(os.environ[SEED_DIR_ENV])
        store = OrderRunsStore(db_path)
        run_id = "20260101_1201"
        run_key = f"tester/{run_id}"
        store.open_run(
            run_meta_row(
                "tester", run_id, "2026-01-01T12:02:00Z",
                mode="match-only", warehouse_mode="first_available",
            )
        )
        tawreed_offer = _store_row()
        store.upsert_run_item(
            run_key,
            {
                "item_code": "m1", "item_name": "SIMULATED ITEM",
                "item_qty": 3, "ordered_total_qty": 0,
                "status": "matched-only", "matched": 1,
                "manual_review_required": 0,
            },
            source_kind="tawreed", source_label="tester",
            stores=[tawreed_offer], store_source="store_details",
            store_selections=[(tawreed_offer, 0)],
        )
        excel_gate_tawreed = {
            **_store_row(),
            "storeProductId": "sp-m2",
        }
        store.upsert_run_item(
            run_key,
            {
                "item_code": "m2", "item_name": "EXCEL GATE ITEM",
                "item_qty": 1, "ordered_total_qty": 0,
                "status": "matched-only", "matched": 1,
                "manual_review_required": 0,
            },
            source_kind="tawreed", source_label="tester",
            stores=[excel_gate_tawreed], store_source="store_details",
            store_selections=[(excel_gate_tawreed, 0)],
        )
        excel_gate_offer = {
            **_store_row(),
            "storeName": "excel-target:البركة شركات@البركة1209.xlsx",
            "storeId": "excel:البركة شركات",
            "storeProductId": "excel-m2",
            "salePrice": 8.5,
        }
        store.upsert_run_item(
            run_key,
            {
                "item_code": "m2", "item_name": "EXCEL GATE ITEM",
                "item_qty": 1, "ordered_total_qty": 0,
                "status": "matched-only", "matched": 1,
                "manual_review_required": 0,
            },
            source_kind="excel-target",
            source_label="البركة شركات@البركة1209.xlsx",
            stores=[excel_gate_offer], store_source="excel_target",
            store_selections=[],
        )
        store.finish_run(run_key)
        store.db.close()

        self._app_test.run()

        self.assertEqual(self._app_test.exception, [])
        headings = [element.value for element in self._app_test.subheader]
        self.assertIn("محاكاة السلة المحتملة حسب المخزن", headings)
        self.assertIn("Alpha", headings)
        excel_heading = "أصناف كانت ستُوجّه إلى Excel Target خارج سلة توريد"
        self.assertIn(excel_heading, headings)
        self.assertLess(
            headings.index(excel_heading), headings.index("نتيجة الشراء الفعلية")
        )


def _project_root() -> str:
    return str(Path(__file__).resolve().parents[4])


def _summary() -> dict:
    return {
        "item_code": "c1", "item_name": "ALFA", "item_qty": 1,
        "ordered_total_qty": 1, "status": "added-to-cart",
        "matched": 1, "manual_review_required": 0,
    }


def _store_row() -> dict:
    return {
        "storeProductId": "sp-a", "storeId": "s:A", "storeName": "Alpha",
        "availableQuantity": 5, "retailPrice": 10.0, "salePrice": 8.0,
        "discount": "20%",
    }


if __name__ == "__main__":
    unittest.main()
