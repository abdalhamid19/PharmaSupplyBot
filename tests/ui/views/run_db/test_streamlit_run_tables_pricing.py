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


with patch.object(_read, 'order_runs_connection', lambda _db: _FakeConn()), \
     patch.object(tbl, 'fetch_item_stores', return_value=fetched):
    _show()
"""


class PricingEnrichmentTests(unittest.TestCase):
    """The store table exposes only ``Provenance`` as a derived column.

    ``net_price`` and ``margin_percent`` were removed because they
    duplicated columns already on the row:
    * ``net_price`` was always equal to ``purchase_price`` (the resolver
      already applies the discount to ``purchase``).
    * ``margin_percent`` was equal to ``discount_percent`` for every
      Tawreed row (``purchase = public × (1 − discount)``).

    The pricing help caption and the Excel-specific caption were also
    removed; the ``provenance`` column already conveys the same context
    in-row, so the captions were redundant.
    """

    def _run(self) -> AppTest:
        app = AppTest.from_string(_DRIVER_SCRIPT, default_timeout=30)
        app.run()
        self.assertEqual(app.exception, [])
        return app

    def test_only_provenance_is_derived(self) -> None:
        """Only ``provenance`` is added; ``net_price`` and ``margin_percent`` are gone."""
        app = self._run()
        self.assertTrue(app.dataframe)
        frame = app.dataframe[-1].value
        self.assertIn("provenance", frame.columns)
        self.assertNotIn(
            "net_price",
            frame.columns,
            "net_price was removed because it duplicated purchase_price.",
        )
        self.assertNotIn(
            "margin_percent",
            frame.columns,
            "margin_percent was removed because it duplicated discount_percent.",
        )

    def test_tawreed_row_keeps_purchase_and_discount(self) -> None:
        """Tawreed rows still expose purchase_price and discount_percent."""
        app = self._run()
        frame = app.dataframe[-1].value
        tawreed = frame[frame["source"] == "👤 Tawreed"].iloc[0]
        self.assertIn("purchase_price", tawreed)
        self.assertIn("discount_percent", tawreed)

    def test_provenance_column_shows_human_label(self) -> None:
        """Provenance text is the friendly label, not the raw enum."""
        app = self._run()
        frame = app.dataframe[-1].value
        labels = set(frame["provenance"])
        self.assertIn("👤 Tawreed", labels)
        self.assertIn("📊 Excel (public → purchase)", labels)

    def test_pricing_help_caption_is_removed(self) -> None:
        """The pricing help caption no longer renders above the expanders."""
        app = self._run()
        captions = [c.value for c in app.caption]
        self.assertFalse(
            any("Public" in c and "Purchase" in c for c in captions),
            f"Pricing help caption must be removed, got {captions!r}",
        )

    def test_excel_run_caption_is_removed(self) -> None:
        """The Excel-target caption no longer renders above the expanders."""
        app = self._run()
        captions = [c.value for c in app.caption]
        self.assertFalse(
            any("Excel-target stores" in c for c in captions),
            f"Excel-run caption must be removed, got {captions!r}",
        )


if __name__ == "__main__":
    unittest.main()
