"""Tests for order-run record wiring between the CLI and persistence."""

from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

from src.cli.commands.cli_order_run_record import (
    active_run_key,
    order_run_options,
)
from src.core.artifact_run import artifact_run
from src.core.config.config_models import (
    AppConfig,
    DatabaseConfig,
    ExcelConfig,
    MatchingConfig,
    ProfileConfig,
    RuntimeConfig,
)


def _app_config(**overrides) -> AppConfig:
    """Return a minimal AppConfig for wiring tests."""
    values = {
        "base_url": "https://seller.tawreed.io/#/login",
        "excel": ExcelConfig(code_col="code", name_col="name", qty_col="qty"),
        "profiles": {"wardany": ProfileConfig(display_name="W", pharmacy_switch={})},
        "selectors": {},
        "warehouse_strategy": {"mode": "max_discount", "min_discount_percent": 15.0},
        "matching": MatchingConfig(),
        "runtime": RuntimeConfig(item_workers=4),
        "database": DatabaseConfig(),
    }
    values.update(overrides)
    return AppConfig(**values)


class ActiveRunKeyTests(unittest.TestCase):
    """The run key must be derivable from the artifact context alone."""

    def test_derived_from_artifact_run(self) -> None:
        """Spawned workers re-enter the same artifact context, so this works there too."""
        with TemporaryDirectory() as temp:
            with artifact_run("order", "wardany", "20260830_1809", Path(temp)):
                self.assertEqual(active_run_key(), "wardany/20260830_1809")

    def test_empty_without_an_active_run(self) -> None:
        """Outside a run there is nothing to attach facts to."""
        self.assertEqual(active_run_key(), "")


class OrderRunOptionsTests(unittest.TestCase):
    """Run metadata must capture what makes two runs comparable."""

    def _options(self, **args) -> dict:
        defaults = {
            "match_only": False,
            "execution_mode": "auto",
            "matching_risk_policy": "safe",
            "excel": "data/input/order_items/x.xlsx",
        }
        defaults.update(args)
        return order_run_options(_app_config(), Namespace(**defaults), "artifacts/x")

    def test_records_warehouse_strategy_from_config(self) -> None:
        """Price comparisons are meaningless without the selection strategy."""
        options = self._options()
        self.assertEqual(options["warehouse_mode"], "max_discount")
        self.assertAlmostEqual(float(options["min_discount_pct"]), 15.0)

    def test_cli_override_wins_over_config(self) -> None:
        """--warehouse-mode must be reflected, not the stale config value."""
        options = self._options(warehouse_mode="first_available", min_discount_percent=0)
        self.assertEqual(options["warehouse_mode"], "first_available")
        self.assertAlmostEqual(float(options["min_discount_pct"]), 0.0)

    def test_mode_reflects_match_only(self) -> None:
        """A match-only run touches no cart and must be distinguishable."""
        self.assertEqual(self._options(match_only=True)["mode"], "match-only")
        self.assertEqual(self._options(match_only=False)["mode"], "order")

    def test_records_execution_and_risk_and_source(self) -> None:
        """These change matching outcomes, so a comparison needs them."""
        options = self._options()
        self.assertEqual(options["execution_mode"], "auto")
        self.assertEqual(options["matching_risk"], "safe")
        self.assertEqual(options["excel_source"], "data/input/order_items/x.xlsx")
        self.assertEqual(options["artifact_dir"], "artifacts/x")

    def test_records_item_workers_from_config(self) -> None:
        """Worker count explains timing differences between runs."""
        self.assertEqual(self._options()["item_workers"], 4)

    def test_cli_item_workers_override_wins(self) -> None:
        """--item-workers is resolved the same way the runner resolves it."""
        self.assertEqual(self._options(item_workers=2)["item_workers"], 2)


if __name__ == "__main__":
    unittest.main()
