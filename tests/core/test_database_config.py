"""Tests for the optional database configuration section."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from src.core.config.config import load_config
from src.core.config.config_factory import build_database_config
from src.core.config.config_models import DatabaseConfig

_MINIMAL = {
    "site": {"base_url": "https://seller.tawreed.io/#/login"},
    "excel": {"code_col": "code", "name_col": "name", "qty_col": "qty"},
    "profiles": {"wardany": {"display_name": "Wardany"}},
}


def _config_with(database: dict | None) -> DatabaseConfig:
    """Load a minimal config, optionally with a database section."""
    with TemporaryDirectory() as temp:
        path = Path(temp) / "config.yaml"
        raw = dict(_MINIMAL)
        if database is not None:
            raw["database"] = database
        path.write_text(yaml.safe_dump(raw), encoding="utf-8")
        return load_config(path).database


class DatabaseConfigTests(unittest.TestCase):
    """Validate defaults, overrides, and the persistence options bridge."""

    def test_defaults_enable_order_run_persistence(self) -> None:
        """Writes are on by default because every path is failure-isolated."""
        config = DatabaseConfig()
        self.assertTrue(config.order_runs_enabled)
        self.assertEqual(config.order_runs_path, "")
        self.assertFalse(config.store_candidates)

    def test_missing_section_uses_defaults(self) -> None:
        """Existing config files must keep working untouched."""
        self.assertEqual(_config_with(None), DatabaseConfig())

    def test_section_values_are_parsed(self) -> None:
        """Operators control the database from state/config.yaml."""
        config = _config_with(
            {
                "order_runs_enabled": False,
                "order_runs_path": "state/other.db",
                "store_candidates": True,
            }
        )
        self.assertFalse(config.order_runs_enabled)
        self.assertEqual(config.order_runs_path, "state/other.db")
        self.assertTrue(config.store_candidates)

    def test_string_booleans_are_coerced(self) -> None:
        """YAML quoting mistakes must not silently disable persistence."""
        config = build_database_config({"database": {"order_runs_enabled": "false"}})
        self.assertFalse(config.order_runs_enabled)

    def test_persistence_options_omit_empty_path(self) -> None:
        """An empty path must fall through to the default, not disable writes."""
        options = DatabaseConfig().persistence_options()
        self.assertTrue(options["enabled"])
        self.assertNotIn("path", options)

    def test_persistence_options_carry_configured_path(self) -> None:
        """A configured path reaches the store without further plumbing."""
        options = DatabaseConfig(order_runs_path="state/other.db").persistence_options()
        self.assertEqual(options["path"], "state/other.db")

    def test_disabled_config_produces_disabled_options(self) -> None:
        """The gate the persistence layer checks comes straight from config."""
        from src.core.ordering.order_run_persistence import persistence_enabled

        options = DatabaseConfig(order_runs_enabled=False).persistence_options()
        self.assertFalse(persistence_enabled(options))


if __name__ == "__main__":
    unittest.main()
