"""End-to-end test for Excel-target snapshot pricing resolution."""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.config.config_models import ExcelTargetConfig
from src.core.config.config import load_config
from src.core.database.order_runs_stores import store_snapshot_rows
from src.core.database.order_runs_keys import order_run_item_key
from src.core.excel_target.excel_target_loader import (
    TargetProduct,
    iter_target_candidates,
)
from src.core.database.order_runs_store import OrderRunsStore
from src.core.config.config_models import DatabaseConfig
from src.cli.commands.cli_order_excel_target import run_excel_target_match_only
from src.core.utils.excel import Item


def _excel_row(
    price: float | None,
    discount: float,
    *,
    code: str = "X-001",
    name: str = "Test Drug 30 tabs",
    price_meaning: str = "public_with_discount",
) -> dict:
    """Build one Excel-target candidate dict with the identity fields the
    snapshot writer needs (``storeId``, ``storeName``)."""
    product = TargetProduct(
        code=code,
        name=name,
        price=price,
        discount_percent=discount,
        price_meaning=price_meaning,
    )
    candidate = iter_target_candidates([product])[0]
    candidate.setdefault("storeId", 9001)
    candidate.setdefault("storeName", "Excel Test Warehouse")
    return candidate


class ExcelSnapshotPricingTests(unittest.TestCase):
    """Excel-target rows must carry both public and purchase prices."""

    _NOW = "2026-09-04T12:00:00"

    def _rows(self, candidate: dict) -> list[dict]:
        return store_snapshot_rows(
            run_key="run1",
            item_key="item1",
            stores=[candidate],
            selections=[],
            now=self._NOW,
            source="excel_target",
        )

    def test_default_meaning_derives_purchase_price(self) -> None:
        """Single-column price is retail; purchase derived from discount."""
        candidate = _excel_row(200.0, 10.0)
        rows = self._rows(candidate)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["public_price"] or 0, 200.0)
        self.assertAlmostEqual(rows[0]["purchase_price"] or 0, 180.0)

    def test_discount_zero_yields_identical_prices(self) -> None:
        """No discount means public == purchase == net."""
        candidate = _excel_row(75.0, 0.0)
        rows = self._rows(candidate)
        self.assertAlmostEqual(rows[0]["public_price"] or 0, 75.0)
        self.assertAlmostEqual(rows[0]["purchase_price"] or 0, 75.0)
        self.assertAlmostEqual(rows[0]["discount_percent"], 0.0)

    def test_purchase_only_meaning_mirrors_both_columns(self) -> None:
        """Operators can opt out of derivation by setting price_meaning."""
        candidate = _excel_row(
            50.0,
            0.0,
            code="X-002",
            name="Another Drug",
            price_meaning="purchase_only",
        )
        rows = self._rows(candidate)
        self.assertAlmostEqual(rows[0]["public_price"] or 0, 50.0)
        self.assertAlmostEqual(rows[0]["purchase_price"] or 0, 50.0)

    def test_blank_price_persists_as_null_and_zero_price_remains_zero(self) -> None:
        """Snapshot persistence must distinguish unknown from a valid zero."""
        blank_rows = self._rows(_excel_row(None, 0.0, code="X-blank"))
        zero_rows = self._rows(_excel_row(0.0, 0.0, code="X-zero"))

        self.assertEqual(blank_rows[0]["public_price"], None)
        self.assertEqual(blank_rows[0]["purchase_price"], None)
        self.assertEqual(zero_rows[0]["public_price"], 0.0)
        self.assertEqual(zero_rows[0]["purchase_price"], 0.0)


class ConfigTests(unittest.TestCase):
    """The new ``price_meaning`` field round-trips through the factory."""

    def test_default_price_meaning(self) -> None:
        cfg = ExcelTargetConfig(name_col="صنف", price_col="سعر", discount_col="الخصم")
        self.assertEqual(cfg.price_meaning, "public_with_discount")

    def test_price_meaning_can_be_overridden(self) -> None:
        cfg = ExcelTargetConfig(
            name_col="صنف",
            price_col="سعر",
            discount_col="الخصم",
            price_meaning="purchase_only",
        )
        self.assertEqual(cfg.price_meaning, "purchase_only")


class ExcelTargetPersistenceContractTests(unittest.TestCase):
    """The Excel-target persister must use the active run database contract."""

    def test_configured_database_contains_excel_row_with_stable_item_key(self) -> None:
        """A custom DB path must receive the row used by the later price gate."""
        config_path = Path(__file__).parents[2] / "cli" / "commands" / "fixtures" / "excel_target_with_target.yaml"
        app_config = load_config(config_path)
        item = Item(code=" 001.0 ", name="  Test Drug 30 tabs ", qty=1)
        catalog = [
            TargetProduct(
                code="001",
                name="Test Drug 30 tabs",
                price=100.0,
                discount_percent=0.0,
                price_meaning="purchase_only",
            )
        ]

        with TemporaryDirectory() as temp:
            db_path = Path(temp) / "configured-order-runs.db"
            app_config = replace(
                app_config,
                database=DatabaseConfig(order_runs_path=str(db_path)),
            )
            summary_path = Path(temp) / "summary.csv"
            run_excel_target_match_only(
                app_config,
                "alnasr",
                [item],
                catalog,
                summary_path=summary_path,
                run_key="wardany/configured-path",
                run_id="configured-path",
            )

            store = OrderRunsStore(db_path)
            rows = store.db.execute_query(
                "select run_key, item_key, source_kind, status from run_items"
            )

        self.assertEqual(
            rows,
            [
                (
                    "wardany/configured-path",
                    order_run_item_key(item.code, item.name),
                    "excel-target",
                    "matched-only",
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
