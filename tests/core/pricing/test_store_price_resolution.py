"""Tests for the single store-pricing resolver seam."""

from __future__ import annotations

import unittest

from src.core.pricing import (
    PROVENANCE_LABELS,
    ResolvedPrices,
    resolve_store_prices,
)


class TawreedResolveTests(unittest.TestCase):
    """Tawreed rows preserve the two distinct prices and only those."""

    def test_both_prices_preserved_with_net(self) -> None:
        """Net equals purchase: the Tawreed purchase is already discounted."""
        store = {
            "retailPrice": 147.0,
            "salePrice": 116.13,
            "discountPercent": 21.0,
        }
        resolved = resolve_store_prices(store, source_kind="tawreed")
        self.assertAlmostEqual(resolved.public_price or 0, 147.0)
        self.assertAlmostEqual(resolved.purchase_price or 0, 116.13)
        self.assertAlmostEqual(resolved.discount_percent, 21.0)
        # Net equals purchase — never apply the discount a second time.
        self.assertAlmostEqual(resolved.net_price or 0, 116.13)
        self.assertEqual(resolved.price_provenance, "tawreed_both")

    def test_only_public_keeps_purchase_null(self) -> None:
        """Do not invent a purchase price from the public one."""
        store = {"retailPrice": 100.0}
        resolved = resolve_store_prices(store, source_kind="tawreed")
        self.assertAlmostEqual(resolved.public_price or 0, 100.0)
        self.assertIsNone(resolved.purchase_price)
        self.assertEqual(resolved.price_provenance, "tawreed_public_only")
        self.assertIsNotNone(resolved.net_price)

    def test_only_purchase_keeps_public_null(self) -> None:
        """Symmetric: missing public stays null."""
        store = {"salePrice": 80.0, "discountPercent": 10.0}
        resolved = resolve_store_prices(store, source_kind="tawreed")
        self.assertIsNone(resolved.public_price)
        self.assertAlmostEqual(resolved.purchase_price or 0, 80.0)
        self.assertEqual(resolved.price_provenance, "tawreed_purchase_only")

    def test_empty_store_is_unknown(self) -> None:
        """Empty input is honest about itself."""
        resolved = resolve_store_prices({}, source_kind="tawreed")
        self.assertIsNone(resolved.public_price)
        self.assertIsNone(resolved.purchase_price)
        self.assertEqual(resolved.discount_percent, 0.0)
        self.assertIsNone(resolved.net_price)
        self.assertEqual(resolved.price_provenance, "unknown")


class ExcelResolveTests(unittest.TestCase):
    """Excel rows carry a single price; the rule depends on ``priceMeaning``."""

    def test_public_with_discount_derives_purchase(self) -> None:
        """Default: column "سعر" is retail, purchase is derived.

        Net equals the derived purchase — applying the discount a second
        time would double-count it.
        """
        store = {"price": 200.0, "discountPercent": 10.0}
        resolved = resolve_store_prices(store, source_kind="excel_target")
        self.assertAlmostEqual(resolved.public_price or 0, 200.0)
        self.assertAlmostEqual(resolved.purchase_price or 0, 180.0)
        self.assertAlmostEqual(resolved.discount_percent, 10.0)
        self.assertAlmostEqual(resolved.net_price or 0, 180.0)
        self.assertEqual(
            resolved.price_provenance, "excel_public_implies_purchase"
        )

    def test_explicit_saleprice_wins_over_derivation(self) -> None:
        """When the loader carried salePrice (purchase), trust it."""
        store = {"price": 200.0, "salePrice": 150.0, "discountPercent": 10.0}
        resolved = resolve_store_prices(store, source_kind="excel_target")
        self.assertAlmostEqual(resolved.public_price or 0, 200.0)
        self.assertAlmostEqual(resolved.purchase_price or 0, 150.0)
        self.assertEqual(
            resolved.price_provenance, "excel_purchase_implies_public"
        )

    def test_excel_purchase_only_means_price_is_what_pharmacy_pays(self) -> None:
        """With purchase_only, public mirrors purchase."""
        store = {"price": 90.0, "discountPercent": 0.0}
        resolved = resolve_store_prices(
            store,
            source_kind="excel_target",
            excel_price_meaning="purchase_only",
        )
        self.assertAlmostEqual(resolved.public_price or 0, 90.0)
        self.assertAlmostEqual(resolved.purchase_price or 0, 90.0)
        self.assertEqual(
            resolved.price_provenance, "excel_purchase_implies_public"
        )

    def test_excel_public_only_keeps_purchase_null(self) -> None:
        """With public_only, no derivation is attempted."""
        store = {"price": 50.0, "discountPercent": 5.0}
        resolved = resolve_store_prices(
            store,
            source_kind="excel_target",
            excel_price_meaning="public_only",
        )
        self.assertAlmostEqual(resolved.public_price or 0, 50.0)
        self.assertIsNone(resolved.purchase_price)
        self.assertEqual(resolved.price_provenance, "tawreed_public_only")


class EdgeCaseTests(unittest.TestCase):
    """Defensive guards against bad input."""

    def test_missing_discount_falls_back_to_first_present_price(self) -> None:
        """With retail and sale set but no explicit discount, net still computes.

        Tawreed's shared parser back-fills a discount from the price gap, so net
        comes out lower than purchase; this test guards that behaviour stays
        consistent.
        """
        store = {"retailPrice": 50.0, "salePrice": 40.0}
        resolved = resolve_store_prices(store, source_kind="tawreed")
        self.assertIsNotNone(resolved.net_price)
        self.assertLessEqual(resolved.net_price or 0, 40.0)

    def test_discount_above_100_is_clamped(self) -> None:
        """A discount >100 is clamped to 100 so we never produce negatives."""
        store = {"retailPrice": 50.0, "salePrice": 10.0, "discountPercent": 150.0}
        resolved = resolve_store_prices(store, source_kind="tawreed")
        self.assertGreaterEqual(resolved.net_price or 0, 0.0)

    def test_zero_prices_yield_zero_net(self) -> None:
        """Zero prices stay zero, never None."""
        store = {"price": 0.0, "discountPercent": 0.0}
        resolved = resolve_store_prices(store, source_kind="excel_target")
        self.assertEqual(resolved.public_price, 0.0)
        self.assertEqual(resolved.purchase_price, 0.0)
        self.assertEqual(resolved.net_price, 0.0)

    def test_all_provenance_labels_have_a_human_readable(self) -> None:
        """Every provenance has a label so the UI never falls back to a raw string."""
        self.assertEqual(len(PROVENANCE_LABELS), 7)
        for label in PROVENANCE_LABELS.values():
            self.assertTrue(label)


class DataclassShapeTests(unittest.TestCase):
    """The dataclass is a frozen value object."""

    def test_dataclass_is_frozen(self) -> None:
        """Mutating a resolved value is a programmer error."""
        resolved = ResolvedPrices(
            public_price=1.0,
            purchase_price=1.0,
            discount_percent=0.0,
            net_price=1.0,
            price_provenance="tawreed_both",
        )
        with self.assertRaises(Exception):
            resolved.public_price = 2.0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()