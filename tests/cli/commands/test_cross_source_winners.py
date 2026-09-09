"""Regression tests for cross-source winner reconciliation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.cli.commands.cli_order import _reconcile_cross_source_winners
from src.core.config.config import load_config
from src.core.config.config_models import DatabaseConfig
from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_store import OrderRunsStore


class CrossSourceWinnerTests(unittest.TestCase):
    """Only the exact source row that supplied the winner is denormalised."""

    def test_reconciliation_does_not_copy_winner_to_other_target_rows(self) -> None:
        config_path = (
            Path(__file__).parent / "fixtures" / "excel_target_with_target.yaml"
        )
        run_key = "wardany/reconcile"
        with TemporaryDirectory() as temp:
            db_path = Path(temp) / "order-runs.db"
            app_config = replace(
                load_config(config_path),
                database=DatabaseConfig(order_runs_path=str(db_path)),
            )
            store = OrderRunsStore(db_path)
            store.open_run(run_meta_row("wardany", "reconcile", started_at="2026-01-01"))
            item = {
                "item_code": "1", "item_name": "TEST ITEM", "item_qty": 1,
                "ordered_total_qty": 0, "status": "matched-only", "matched": 1,
                "winner_store_product_id": "", "winner_store_key": "",
            }
            baraka = {
                "storeProductId": "baraka-product", "storeId": 1,
                "storeName": "Baraka", "productName": "TEST ITEM",
                "availableQuantity": 1, "salePrice": 10.0,
                "discountPercent": 0.0,
            }
            store.upsert_run_item(
                run_key, item, source_kind="excel-target",
                source_label="baraka@baraka.xlsx", store_source="excel_target",
                store_source_owner="baraka", stores=[baraka],
                store_selections=[(baraka, 0)],
            )
            rejected = dict(item, status="no-results", matched=0,
                            winner_store_product_id="stale")
            store.upsert_run_item(
                run_key, rejected, source_kind="excel-target",
                source_label="qaysar", store_source="excel_target",
                store_source_owner="qaysar", stores=[], store_selections=[],
            )

            _reconcile_cross_source_winners(app_config, "wardany", "reconcile")
            rows = store.db.execute_query(
                "select source_label, status, winner_store_product_id, "
                "winner_store_key from run_items where run_key=? "
                "order by source_label",
                (run_key,),
            )

        self.assertEqual(rows[0][0], "baraka@baraka.xlsx")
        self.assertIsNotNone(rows[0][2])
        self.assertIsNotNone(rows[0][3])
        self.assertEqual(rows[1], ("qaysar", "no-results", None, None))


if __name__ == "__main__":
    unittest.main()
