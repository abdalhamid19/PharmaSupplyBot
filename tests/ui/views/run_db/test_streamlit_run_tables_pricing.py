"""AppTest coverage for the honest pricing display in 'Offering stores per item'."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


_DRIVER_SCRIPT = """
import pandas as pd
from unittest.mock import patch
from src.ui.views.run_db import streamlit_run_tables as tbl


def _show():
    items = [{
        'item_key': 'ITEM-1',
        'item_code': 'C1',
        'item_name': 'DECLOPHEN GEL',
        'stores_offering': 3,
    }]
    tbl.render_item_stores_expander(items, 'run-key-1')


fetched = [
    {
        'store_key': 'store_details:1', 'store_product_id': 'P1',
        'source': 'store_details', 'public_price': 147.0,
        'purchase_price': 116.13, 'discount_percent': 21.0,
        'currency': 'EGP', 'available_qty': 5, 'is_winner': 1,
        'rank_by_discount': 1, 'ordered_qty': 5, 'priority': 10,
        'price_provenance': 'tawreed_both',
    },
    {
        'store_key': 'excel_target:1', 'store_product_id': 'E1',
        'source': 'excel_target', 'public_price': 80.0,
        'purchase_price': 80.0, 'discount_percent': 5.0,
        'currency': 'EGP', 'available_qty': 3, 'is_winner': 0,
        'rank_by_discount': 2, 'ordered_qty': 0, 'priority': None,
        'price_provenance': 'excel_public_implies_purchase',
    },
    {
        'store_key': 'excel_target:2', 'store_product_id': 'E2',
        'source': 'excel_target', 'public_price': 90.0,
        'purchase_price': 90.0, 'discount_percent': 0.0,
        'currency': 'EGP', 'available_qty': 0, 'is_winner': 0,
        'rank_by_discount': 3, 'ordered_qty': 0, 'priority': None,
        'price_provenance': 'excel_purchase_implies_public',
    },
]


class _FakeConn:
    def execute_query(self, _sql, _params):
        return [(1,)]


import src.core.database.order_runs_read as _read
_read.order_runs_connection = lambda _db: _FakeConn()


with patch.object(tbl, 'fetch_item_stores', return_value=fetched):
    _show()
"""


class PricingEnrichmentTests(unittest.TestCase):
    """The store table gains ``net_price``, ``margin_percent`` and ``provenance``."""

    def _run(self) -> AppTest:
        app = AppTest.from_string(_DRIVER_SCRIPT, default_timeout=30)
        app.run()
        self.assertEqual(app.exception, [])
        return app

    def test_dataframe_has_derived_columns(self) -> None:
        """All three derived columns appear in the rendered dataframe."""
        app = self._run()
        self.assertTrue(app.dataframe)
        frame = app.dataframe[-1].value
        self.assertIn("net_price", frame.columns)
        self.assertIn("margin_percent", frame.columns)
        self.assertIn("provenance", frame.columns)

    def test_tawreed_row_has_margin_hint(self) -> None:
        """Tawreed row carries a margin between public and purchase."""
        app = self._run()
        frame = app.dataframe[-1].value
        tawreed = frame[frame["source"] == "👤 Tawreed"].iloc[0]
        self.assertAlmostEqual(tawreed["margin_percent"], 21.0, delta=0.5)

    def test_excel_row_net_equals_public_after_discount(self) -> None:
        """Excel row net = public × (1 − discount)."""
        app = self._run()
        frame = app.dataframe[-1].value
        excel = frame[frame["source"] == "📊 Excel target"]
        discounted = excel[excel["discount_percent"] == 5.0].iloc[0]
        self.assertAlmostEqual(discounted["net_price"], 76.0)

    def test_provenance_column_shows_human_label(self) -> None:
        """Provenance text is the friendly label, not the raw enum."""
        app = self._run()
        frame = app.dataframe[-1].value
        labels = set(frame["provenance"])
        self.assertIn("👤 Tawreed", labels)
        self.assertIn("📊 Excel (public → purchase)", labels)

    def test_caption_with_pricing_help_is_rendered(self) -> None:
        """The pricing help caption appears above the per-item expanders."""
        app = self._run()
        captions = [c.value for c in app.caption]
        self.assertTrue(
            any("Public" in c and "Purchase" in c for c in captions),
            f"Expected pricing help caption, got {captions!r}",
        )

    def test_excel_run_caption_appears_when_excel_rows_exist(self) -> None:
        """An extra caption explains Excel-target pricing semantics."""
        app = self._run()
        captions = [c.value for c in app.caption]
        self.assertTrue(
            any("Excel-target stores" in c for c in captions),
            f"Expected Excel-run caption, got {captions!r}",
        )


if __name__ == "__main__":
    unittest.main()