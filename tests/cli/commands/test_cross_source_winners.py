"""Regression tests for cross-source winner reconciliation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.cli.commands.cli_order import (
    _cross_source_should_replace,
    _reconcile_cross_source_winners,
)
from src.core.config.config import load_config
from src.core.config.config_models import DatabaseConfig
from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_store import OrderRunsStore
from src.core.database.warehouse_winner_selection import PREFERRED_WAREHOUSES


class CrossSourceWinnerTests(unittest.TestCase):
    """Only the exact source row that supplied the winner is denormalised."""

    def test_tawreed_cheapest_price_wins_inside_quarter_pound(self) -> None:
        preferred = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[0],
            "store_key": "preferred",
            "store_product_id": "preferred-product",
            "purchase_price": 100.2,
        }
        cheaper = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[1],
            "store_key": "cheaper",
            "store_product_id": "cheaper-product",
            "purchase_price": 100.0,
        }
        self.assertFalse(_cross_source_should_replace(preferred, cheaper))
        self.assertTrue(_cross_source_should_replace(cheaper, preferred))

    def test_equal_tawreed_price_still_uses_configured_priority(self) -> None:
        preferred = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[0],
            "store_key": "preferred",
            "store_product_id": "preferred-product",
            "purchase_price": 100.0,
        }
        other = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[1],
            "store_key": "other",
            "store_product_id": "other-product",
            "purchase_price": 100.0,
        }
        self.assertTrue(_cross_source_should_replace(preferred, other))
        self.assertFalse(_cross_source_should_replace(other, preferred))

    def test_equal_unlisted_tawreed_prices_use_stable_name_order(self) -> None:
        second = {
            "source": "store_details",
            "store_name": "Unlisted B",
            "store_key": "b",
            "store_product_id": "b",
            "purchase_price": 100.0,
        }
        first = {
            "source": "store_details",
            "store_name": "Unlisted A",
            "store_key": "a",
            "store_product_id": "a",
            "purchase_price": 100.0,
        }
        self.assertTrue(_cross_source_should_replace(first, second))
        self.assertFalse(_cross_source_should_replace(second, first))

    def test_equal_tie_uses_source_label_when_store_name_is_missing(self) -> None:
        first = {
            "source": "store_details", "source_label": "Unlisted A",
            "store_name": "", "store_key": "z", "store_product_id": "z",
            "purchase_price": 100.0,
        }
        second = {
            "source": "store_details", "source_label": "Unlisted B",
            "store_name": "", "store_key": "a", "store_product_id": "a",
            "purchase_price": 100.0,
        }
        self.assertTrue(_cross_source_should_replace(first, second))
        self.assertFalse(_cross_source_should_replace(second, first))

    def test_tawreed_price_difference_of_quarter_pound_prefers_lower_price(self) -> None:
        preferred = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[0],
            "store_key": "preferred",
            "store_product_id": "preferred-product",
            "purchase_price": 100.25,
        }
        cheaper = {
            "source": "store_details",
            "store_name": PREFERRED_WAREHOUSES[1],
            "store_key": "cheaper",
            "store_product_id": "cheaper-product",
            "purchase_price": 100.0,
        }
        self.assertTrue(_cross_source_should_replace(cheaper, preferred))

    def _winner_source(
        self,
        excel_price: float,
        tawreed_price: float,
        *,
        excel_discount: float = 0.0,
        tawreed_discount: float = 0.0,
        excel_available: int = 1,
        tawreed_available: int = 1,
        min_discount_pct: float | None = None,
        excel_currency: str = "",
        tawreed_currency: str = "",
    ) -> str:
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
            store.open_run(run_meta_row(
                "wardany", "reconcile", started_at="2026-01-01",
                min_discount_pct=min_discount_pct,
            ))
            item = {
                "item_code": "1", "item_name": "TEST ITEM", "item_qty": 1,
                "ordered_total_qty": 0, "status": "matched-only", "matched": 1,
            }
            excel = {
                "storeProductId": "excel-product", "storeId": 1,
                "storeName": "Excel", "productName": "TEST ITEM",
                "availableQuantity": excel_available, "salePrice": excel_price,
                "discountPercent": excel_discount, "currency": excel_currency,
                "priceMeaning": "purchase_only",
            }
            tawreed = {
                "storeProductId": "tawreed-product", "storeId": 2,
                "storeName": "Tawreed", "productName": "TEST ITEM",
                "availableQuantity": tawreed_available, "salePrice": tawreed_price,
                "discountPercent": tawreed_discount, "currency": tawreed_currency,
                "priceMeaning": "purchase_only",
            }
            store.upsert_run_item(
                run_key, item, source_kind="excel-target",
                source_label="baraka@baraka.xlsx", store_source="excel_target",
                stores=[excel], store_selections=[(excel, 0)],
            )
            store.upsert_run_item(
                run_key, item, source_kind="tawreed", source_label="tawreed",
                store_source="store_details", stores=[tawreed],
                store_selections=[(tawreed, 0)],
            )

            _reconcile_cross_source_winners(app_config, "wardany", "reconcile")
            rows = store.db.execute_query(
                "select source from run_item_stores where run_key=? and is_winner=1",
                (run_key,),
            )
            return str(rows[0][0]) if rows else "no-winner"

    def test_excel_target_wins_when_purchase_price_is_lower(self) -> None:
        self.assertEqual(self._winner_source(90, 100, tawreed_discount=99), "excel_target")

    def test_excel_target_wins_equal_purchase_price_without_discount_tiebreak(self) -> None:
        self.assertEqual(self._winner_source(100, 100, tawreed_discount=99), "excel_target")

    def test_tawreed_wins_when_purchase_price_is_lower(self) -> None:
        self.assertEqual(self._winner_source(110, 100, excel_discount=99), "store_details")

    def test_out_of_stock_tawreed_offer_cannot_become_the_winner(self) -> None:
        self.assertEqual(
            self._winner_source(100, 90, tawreed_available=0), "excel_target"
        )

    def test_saved_minimum_discount_filters_tawreed(self) -> None:
        self.assertEqual(
            self._winner_source(
                100, 90, excel_discount=10, tawreed_discount=9,
                min_discount_pct=10,
            ),
            "excel_target",
        )

    def test_saved_minimum_discount_filters_both_sources(self) -> None:
        self.assertEqual(
            self._winner_source(
                80, 90, excel_discount=9, tawreed_discount=0,
                min_discount_pct=10,
            ),
            "no-winner",
        )

    def test_excel_target_meeting_saved_minimum_discount_can_win(self) -> None:
        self.assertEqual(
            self._winner_source(
                80, 90, excel_discount=10, tawreed_discount=0,
                min_discount_pct=10,
            ),
            "excel_target",
        )

    def test_currency_metadata_does_not_prevent_price_comparison(self) -> None:
        self.assertEqual(
            self._winner_source(
                100, 90, excel_currency="EGP", tawreed_currency="USD"
            ),
            "store_details",
        )

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
