"""Tests for the Excel target config additions.

The Excel target catalog is owned by a pharmacy that sells to end
customers at a retail price. To make the Run Results tab legible we
need two new config keys:

* ``store_id`` — stable identifier used as ``store_key`` in
  ``run_item_stores`` so the per-item offering-store expander shows a
  distinct row per catalog instead of an anonymous blank entry.
* ``store_name`` — human-readable label used as ``store_name`` in
  ``run_item_stores`` and surfaced in the UI.

These tests pin down the config parsing behaviour.
"""

from __future__ import annotations

from unittest import TestCase

from src.core.config.config_factory import build_excel_target
from src.core.config.config_models import ExcelTargetConfig


class TestExcelTargetStoreIdentity(TestCase):
    """``store_id`` and ``store_name`` flow into ``ExcelTargetConfig``."""

    def test_defaults_when_missing(self) -> None:
        """Without config keys the dataclass defaults to empty strings."""
        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
            }
        )
        self.assertIsInstance(cfg, ExcelTargetConfig)
        self.assertEqual(cfg.store_id, "")
        self.assertEqual(cfg.store_name, "")

    def test_store_id_is_parsed(self) -> None:
        """``store_id`` key surfaces on the config object."""
        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
                "store_id": "excel-store-001",
            }
        )
        self.assertEqual(cfg.store_id, "excel-store-001")

    def test_store_name_is_parsed(self) -> None:
        """``store_name`` key surfaces on the config object."""
        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
                "store_name": "صيدلية المعادي",
            }
        )
        self.assertEqual(cfg.store_name, "صيدلية المعادي")

    def test_store_id_and_store_name_together(self) -> None:
        """Both keys can be supplied at the same time."""
        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
                "store_id": "excel-store-002",
                "store_name": "صيدلية الجزيرة",
            }
        )
        self.assertEqual(cfg.store_id, "excel-store-002")
        self.assertEqual(cfg.store_name, "صيدلية الجزيرة")

    def test_store_id_falls_back_to_target_key_when_empty(self) -> None:
        """When ``store_id`` is missing, helpers should fall back to ``target_key``.

        The reconciler needs a non-empty ``store_key`` for the WHERE
        clause that flips ``is_winner``. Empty values would break the
        unique UPDATE in ``_reconcile_cross_source_winners``. We verify
        the helper that resolves the fallback returns the key.

        When a ``source_file`` is provided the helper appends it so
        multiple files under one target_key still group as distinct
        rows in ``run_item_stores``.
        """
        from src.cli.commands.cli_order_excel_target import (
            resolve_excel_target_store_identity,
        )

        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
            }
        )
        store_key, store_name = resolve_excel_target_store_identity(
            target_key="alnasr",
            source_file="warehouse.xlsx",
            config=cfg,
        )
        self.assertEqual(store_key, "excel-target:alnasr@warehouse.xlsx")
        self.assertTrue(store_name)  # non-empty
        self.assertIn("alnasr", store_name)

        # No source file: bare key.
        bare_key, bare_name = resolve_excel_target_store_identity(
            target_key="alnasr",
            source_file="",
            config=cfg,
        )
        self.assertEqual(bare_key, "excel-target:alnasr")
        self.assertIn("alnasr", bare_name)

    def test_store_id_used_directly_when_configured(self) -> None:
        """When ``store_id`` is set, the helper uses it verbatim."""
        from src.cli.commands.cli_order_excel_target import (
            resolve_excel_target_store_identity,
        )

        cfg = build_excel_target(
            {
                "name_col": "صنف",
                "price_col": "سعر",
                "discount_col": "الخصم",
                "store_id": "my-store-id",
                "store_name": "مخزن تجريبي",
            }
        )
        store_key, store_name = resolve_excel_target_store_identity(
            target_key="ignored",
            source_file="ignored.xlsx",
            config=cfg,
        )
        self.assertEqual(store_key, "my-store-id")
        self.assertEqual(store_name, "مخزن تجريبي")