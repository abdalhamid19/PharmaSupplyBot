"""Test purchase-price-first warehouse selection and priority tie-breaking."""
import unittest
from src.tawreed.store.tawreed_store_selection import (
    choose_next_store_for_remaining_quantity,
    _normalize_store_name,
    _stores_match,
    calculate_warehouse_priority_score,
)


class TestWarehousePriority(unittest.TestCase):
    """Test warehouse priority selection."""

    def test_equal_discount_prefers_higher_priority(self):
        """When discounts equal (within 0.3%), prefer higher priority."""
        stores = [
            _store("الريان", 10, 15.0),
            _store("البركه", 10, 15.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("البركه", choice.store["storeName"])

    def test_cheapest_price_wins_when_gap_is_over_025(self):
        """The lower purchase price wins even when the gap is over 0.25 EGP."""
        stores = [
            _store("البركه", 10, 10.0),
            _store("الريان", 10, 20.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("الريان", choice.store["storeName"])

    def test_cheapest_price_wins_inside_025_even_over_preferred_warehouse(self):
        """A lower purchase price wins even when the gap is under 0.25 EGP."""
        stores = [
            _store("الريان", 10, 15.1),
            _store("البركه", 10, 15.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("الريان", choice.store["storeName"])

    def test_cheapest_price_wins_when_gap_is_over_025_with_discount_data(self):
        """The price rule still wins when offers also carry discount data."""
        stores = [
            _store("البركه", 10, 15.0),
            _store("الريان", 10, 15.5),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("الريان", choice.store["storeName"])

    def test_unknown_warehouse_gets_low_priority(self):
        """Unknown warehouses get priority_score=999."""
        stores = [
            _store("مخزن غير معروف", 10, 15.0),
            _store("البركه", 10, 15.0),
        ]
        preferred = ["شركه البركه (الجيزه)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("البركه", choice.store["storeName"])

    def test_priority_order_respected(self):
        """All 7 warehouses ranked correctly."""
        stores = [
            _store("الريان", 10, 15.0),
            _store("نيو سيدرا", 10, 15.0),
            _store("البركه", 10, 15.0),
            _store("الماسه", 10, 15.0),
            _store("الشفاء ميدكو", 10, 15.0),
        ]
        preferred = [
            "شركه البركه (الجيزه)",
            "شركه الماسه (مالك سابقا ) (الجيزه)",
            "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)",
            "شركه الفا فارما (الجيزه)",
            "شركه مصر مديكال (الجيزه)",
            "شركه نيو سيدرا (القليوبيه)",
            "شركه الريان (القاهره)",
        ]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("البركه", choice.store["storeName"])


class TestStoreFuzzyMatching(unittest.TestCase):
    """Test store name normalization and fuzzy matching."""

    def test_normalize_removes_punctuation(self):
        """Normalization removes punctuation."""
        result = _normalize_store_name("شركه البركه (الجيزه)")
        self.assertIn("البركه", result)
        self.assertIn("الجيزه", result)

    def test_stores_match_exact(self):
        """Exact names match."""
        self.assertTrue(_stores_match("البركه", "البركه"))

    def test_stores_match_fuzzy(self):
        """Fuzzy matching works for partial names."""
        self.assertTrue(_stores_match("البركه", "شركه البركه (الجيزه)"))

    def test_calculate_priority_score(self):
        """Priority score calculated correctly."""
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        self.assertEqual(calculate_warehouse_priority_score("البركه", preferred), 1)
        self.assertEqual(calculate_warehouse_priority_score("الريان", preferred), 2)
        self.assertEqual(calculate_warehouse_priority_score("غير معروف", preferred), 999)

    def test_calculate_priority_score_normalizes_common_arabic_spelling(self):
        preferred = ["شركه الفا فارما (الجيزه)"]
        self.assertEqual(
            calculate_warehouse_priority_score("شركة الفا فارما (الجيزه)", preferred),
            1,
        )

    def test_calculate_priority_score_ignores_arabic_tatweel(self):
        preferred = ["شركه الفا فارما (الجيزه)"]
        self.assertEqual(
            calculate_warehouse_priority_score("شـركة الفا فارما (الجيزه)", preferred),
            1,
        )


class TestMaxAvailableMode(unittest.TestCase):
    """Test price priority and warehouse tie-breaking in max_available mode."""

    def test_max_available_uses_priority_for_equal_qty(self):
        """When quantities equal, priority breaks tie."""
        stores = [
            _store("الريان", 100, 10.0),
            _store("البركه", 100, 10.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_available", RuntimeError, 0.0, preferred
        )
        self.assertIn("البركه", choice.store["storeName"])

    def test_max_available_uses_quantity_within_same_price_tier_and_rank(self):
        stores = [
            _store("مخزن غير معروف أ", 100, 10.0, purchase_price=10.0),
            _store("مخزن غير معروف ب", 2, 10.0, purchase_price=10.0),
        ]
        preferred = ["شركه البركه (الجيزه)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_available", RuntimeError, 0.0, preferred
        )
        self.assertIn("مخزن غير معروف أ", choice.store["storeName"])


class TestFirstAvailableMode(unittest.TestCase):
    def test_first_available_uses_preference_before_api_order(self):
        stores = [_store("الريان", 54, 35.0), _store("الفا فارما", 53, 35.0)]
        preferred = ["شركه الفا فارما (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "first_available", RuntimeError, 0.0, preferred
        )
        self.assertIn("الفا", choice.store["storeName"])

    def test_alpha_wins_three_modes_without_reordering_preferences(self):
        stores = [
            _store("البركه (الجيزه)", 18, 33.0, purchase_price=18.40),
            _store("عنايه للادويه (الجيزه)", 54, 35.0, purchase_price=18.20),
            _store("الفا فارما (الجيزه)", 53, 35.0, purchase_price=18.20),
            _store("التحرير (الجيزه)", 5, 34.0, purchase_price=18.48),
        ]
        preferred = [
            "شركه البركه (الجيزه)",
            "شركه الماسه (مالك سابقا ) (الجيزه)",
            "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)",
            "شركه الفا فارما (الجيزه)",
        ]

        for mode in ("first_available", "max_available", "max_discount"):
            with self.subTest(mode=mode):
                choice = choose_next_store_for_remaining_quantity(
                    stores, None, mode, RuntimeError, 0.0, preferred
                )
                self.assertIn("الفا", choice.store["storeName"])


def _store(
    name: str, qty: int, discount: float, *, purchase_price: float | None = None
) -> dict:
    """Helper to create store dict."""
    return {
        "storeName": f"شركه {name}",
        "availableQuantity": qty,
        "retailPrice": 100.0,
        "salePrice": (
            purchase_price
            if purchase_price is not None
            else 100.0 * (1 - discount / 100)
        ),
        "storeProductId": f"id_{name}",
    }


if __name__ == "__main__":
    unittest.main()
