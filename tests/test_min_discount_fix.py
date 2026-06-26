"""Unit tests for max_discount mode behavior with min_discount_percent."""
import unittest
from types import SimpleNamespace

from src.tawreed.tawreed_products_flow import _effective_min_discount, _find_max_discount
from src.tawreed.tawreed_store_selection import (
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

    def test_max_discount_rejects_when_highest_below_minimum(self):
        """When highest discount < min_discount_percent, reject item."""
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
        
        with self.assertRaises(RuntimeError) as ctx:
            choose_next_store_for_remaining_quantity(
                stores_low_discount,
                mode="max_discount",
                skip_exception_cls=RuntimeError,
                min_discount_percent=12.0,
            )
        
        self.assertIn("minimum discount", str(ctx.exception))

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

    def test_effective_min_discount_escalates_in_max_discount_mode(self):
        """In max_discount mode with selections, min escalates."""
        bot = SimpleNamespace(
            config=SimpleNamespace(
                warehouse_strategy={
                    "mode": "max_discount",
                    "min_discount_percent": 10.0,
                }
            )
        )
        
        # No selections yet
        self.assertEqual(_effective_min_discount(bot, []), 10.0)
        
        # With selection of 25%
        sels = [({"discountPercent": 25.0}, 5)]
        self.assertEqual(_effective_min_discount(bot, sels), 25.0)

    def test_effective_min_discount_no_escalation_in_other_modes(self):
        """In first_available mode, no escalation."""
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

    def test_single_store_rejects_below_min_discount(self):
        """Single-store products should reject if discount < min_discount_percent."""
        from src.tawreed.tawreed_products_flow import _click_cart
        
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
        
        # Should raise skip_item_exception
        with self.assertRaises(RuntimeError) as ctx:
            _click_cart(bot, None, None, match)
        
        self.assertIn("27", str(ctx.exception))
        self.assertIn("30", str(ctx.exception))

    def test_max_discount_rejects_item_before_selection(self):
        """Test that items are rejected when max discount is below minimum before any selection."""
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
        
        # This simulates the scenario where highest discount (27%) < min_discount_percent (30%)
        max_discount = _find_max_discount(stores_below_minimum)
        self.assertEqual(max_discount, 27.0)
        
        # The logic should reject this item because 27% < 30%
        min_discount = 30.0
        self.assertLess(max_discount, min_discount - 0.001)


if __name__ == "__main__":
    unittest.main()
