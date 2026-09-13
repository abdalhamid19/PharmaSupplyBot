"""Unit tests for max_discount mode behavior with min_discount_percent."""
import unittest
from types import SimpleNamespace

from src.tawreed.products.tawreed_products_flow import _effective_min_discount, _find_max_discount
from src.tawreed.store.tawreed_store_selection import (
    available_store_choices,
    choose_next_store_for_remaining_quantity,
)


class TestMaxDiscountWithMinimum(unittest.TestCase):
    """Test max_discount mode: highest discount stores only."""

    def setUp(self):
        """Set up test fixtures."""
        self.stores = [
            {
                "storeProductId": 1,
                "availableQuantity": 5,
                "discountPercent": 25.0,
                "storeName": "Store A",
            },
            {
                "storeProductId": 2,
                "availableQuantity": 8,
                "discountPercent": 15.0,
                "storeName": "Store B",
            },
            {
                "storeProductId": 3,
                "availableQuantity": 12,
                "discountPercent": 12.0,
                "storeName": "Store C",
            },
        ]

    def test_find_max_discount_returns_highest(self):
        """_find_max_discount returns the highest discount value."""
        max_discount = _find_max_discount(self.stores)
        self.assertEqual(max_discount, 25.0)

    def test_find_max_discount_with_multiple_same_max(self):
        """_find_max_discount works when multiple stores have max discount."""
        stores = [
            {"storeProductId": 1, "availableQuantity": 5, "discountPercent": 20.0},
            {"storeProductId": 2, "availableQuantity": 8, "discountPercent": 20.0},
            {"storeProductId": 3, "availableQuantity": 12, "discountPercent": 15.0},
        ]
        max_discount = _find_max_discount(stores)
        self.assertEqual(max_discount, 20.0)

    def test_max_discount_selects_highest_discount_store(self):
        """In max_discount mode, select the store with highest discount."""
        choice = choose_next_store_for_remaining_quantity(
            self.stores,
            mode="max_discount",
            min_discount_percent=0,
        )
        self.assertIsNotNone(choice)
        self.assertEqual(choice.discount_percent, 25.0)
        self.assertEqual(choice.store["storeName"], "Store A")

    def test_max_discount_mode_filters_tawreed_below_configured_floor(self):
        """Tawreed stores below the configured floor are not eligible."""
        stores_low_discount = [
            {
                "storeProductId": 1,
                "availableQuantity": 10,
                "discountPercent": 10.0,
                "storeName": "Store D",
            },
            {
                "storeProductId": 2,
                "availableQuantity": 8,
                "discountPercent": 8.0,
                "storeName": "Store E",
            },
        ]
        
        with self.assertRaisesRegex(RuntimeError, "discount tier 30%"):
            choose_next_store_for_remaining_quantity(
                stores_low_discount,
                mode="max_discount",
                skip_exception_cls=RuntimeError,
                min_discount_percent=30.0,
            )

    def test_max_discount_accepts_when_highest_meets_minimum(self):
        """When highest discount >= min_discount_percent, accept."""
        choice = choose_next_store_for_remaining_quantity(
            self.stores,
            mode="max_discount",
            min_discount_percent=12.0,
        )
        self.assertIsNotNone(choice)
        self.assertEqual(choice.discount_percent, 25.0)

    def test_available_store_choices_filters_by_minimum(self):
        """available_store_choices filters stores correctly."""
        # With min = 15%, should get 2 stores (25% and 15%)
        choices = available_store_choices(self.stores, min_discount_percent=15.0)
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0].discount_percent, 25.0)
        self.assertEqual(choices[1].discount_percent, 15.0)

    def test_configured_floor_applies_before_max_discount_continuation(self):
        """The run floor applies initially, then max mode preserves its tier."""
        bot = SimpleNamespace(
            config=SimpleNamespace(
                warehouse_strategy={
                    "mode": "max_discount",
                    "min_discount_percent": 10.0,
                }
            )
        )
        
        # The configured floor applies before selecting any Tawreed offer.
        self.assertEqual(_effective_min_discount(bot, []), 10.0)
        
        # With selection of 25%
        sels = [({"discountPercent": 25.0}, 5)]
        self.assertEqual(_effective_min_discount(bot, sels), 25.0)

    def test_configured_floor_applies_in_first_available_mode(self):
        """All selection modes receive the configured Tawreed floor."""
        bot = SimpleNamespace(
            config=SimpleNamespace(
                warehouse_strategy={
                    "mode": "first_available",
                    "min_discount_percent": 10.0,
                }
            )
        )
        
        sels = [({"discountPercent": 25.0}, 5)]
        self.assertEqual(_effective_min_discount(bot, sels), 10.0)

    def test_single_tawreed_store_below_floor_is_rejected_before_cart_or_recording(self):
        """A single-store Tawreed offer must pass the floor before any side effect."""
        from src.tawreed.products.tawreed_products_flow import _click_cart
        from unittest.mock import patch
        
        bot = SimpleNamespace(
            config=SimpleNamespace(
                warehouse_strategy={
                    "mode": "max_discount",
                    "min_discount_percent": 30.0,
                }
            ),
            skip_item_exception=RuntimeError
        )
        
        match = SimpleNamespace(
            data={"discountPercent": 27.0, "storeName": "Test Store"}
        )
        
        with patch("src.tawreed.products.tawreed_products_flow.record_single_store") as record, \
                patch("src.tawreed.products.tawreed_products_flow._record_search_row_as_store") as snapshot, \
                patch("src.tawreed.products.tawreed_products_flow.wait_for_row_to_settle") as wait, \
                patch("src.tawreed.products.tawreed_products_flow.cart_button") as button:
            with self.assertRaisesRegex(RuntimeError, "below the configured minimum"):
                _click_cart(bot, object(), None, match)
        record.assert_not_called()
        snapshot.assert_not_called()
        wait.assert_not_called()
        button.assert_not_called()

    def test_max_discount_with_no_eligible_tawreed_offer_is_skipped(self):
        """Max-discount mode skips when every Tawreed offer misses the floor."""
        from src.tawreed.api.tawreed_api_flow_multistore import (
            _validate_max_discount_if_needed,
        )
        stores_below_minimum = [
            {
                "storeProductId": 1,
                "availableQuantity": 10,
                "discountPercent": 27.0,  # Below 30% minimum
                "storeName": "Store A",
            },
            {
                "storeProductId": 2,
                "availableQuantity": 8,
                "discountPercent": 25.0,
                "storeName": "Store B",
            },
        ]
        
        bot = SimpleNamespace(
            config=SimpleNamespace(
                warehouse_strategy={"min_discount_percent": 30.0}
            ),
            skip_item_exception=RuntimeError,
        )
        self.assertEqual(
            _validate_max_discount_if_needed(bot, "max_discount", stores_below_minimum),
            27.0,
        )
        with self.assertRaisesRegex(RuntimeError, "discount tier 30%"):
            choose_next_store_for_remaining_quantity(
                stores_below_minimum,
                mode="max_discount",
                skip_exception_cls=RuntimeError,
                min_discount_percent=_effective_min_discount(bot, []),
            )


if __name__ == "__main__":
    unittest.main()
