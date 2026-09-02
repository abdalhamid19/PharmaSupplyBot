"""Tests for the source-label resolver used in the Run DB items table."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.ui.views.run_db.streamlit_run_db_page import (
    _build_source_label_resolver,
)


class SourceLabelResolverTests(unittest.TestCase):
    def test_resolves_tawreed_profile_display_name(self) -> None:
        profile = SimpleNamespace(display_name="صيدلية الورداني")
        cfg = SimpleNamespace(
            profiles={"wardany": profile},
            excel_targets={},
        )
        resolver = _build_source_label_resolver(cfg)
        self.assertEqual(resolver("tawreed", "wardany"), "صيدلية الورداني")

    def test_resolves_excel_target_display_name(self) -> None:
        target = SimpleNamespace(display_name="المخازن الادويه المبوية")
        cfg = SimpleNamespace(
            profiles={},
            excel_targets={"drug-warehouses": target},
        )
        resolver = _build_source_label_resolver(cfg)
        self.assertEqual(
            resolver("excel-target", "drug-warehouses"),
            "المخازن الادويه المبوية",
        )

    def test_falls_back_to_raw_key_when_display_name_missing(self) -> None:
        profile = SimpleNamespace(display_name="")
        cfg = SimpleNamespace(
            profiles={"wardany": profile},
            excel_targets={},
        )
        resolver = _build_source_label_resolver(cfg)
        self.assertEqual(resolver("tawreed", "wardany"), "wardany")

    def test_falls_back_to_raw_key_when_kind_unknown(self) -> None:
        cfg = SimpleNamespace(profiles={}, excel_targets={})
        resolver = _build_source_label_resolver(cfg)
        self.assertEqual(resolver("tawreed", "al-jazira"), "al-jazira")

    def test_returns_none_when_app_config_is_missing(self) -> None:
        self.assertIsNone(_build_source_label_resolver(None))


if __name__ == "__main__":
    unittest.main()
