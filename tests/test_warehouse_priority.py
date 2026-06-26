"""Test warehouse priority system with discount tolerance."""
import unittest
from src.tawreed.tawreed_store_selection import (
    choose_next_store_for_remaining_quantity,
    _normalize_store_name,
    _stores_match,
    _calculate_priority_score,
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

    def test_higher_discount_wins_over_priority(self):
        """Higher discount wins even if lower priority."""
        stores = [
            _store("البركه", 10, 10.0),
            _store("الريان", 10, 20.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("الريان", choice.store["storeName"])

    def test_within_tolerance_uses_priority(self):
        """Discounts within 0.3% are considered equal."""
        stores = [
            _store("الريان", 10, 15.1),
            _store("البركه", 10, 15.0),
        ]
        preferred = ["شركه البركه (الجيزه)", "شركه الريان (القاهره)"]
        choice = choose_next_store_for_remaining_quantity(
            stores, None, "max_discount", RuntimeError, 0.0, preferred
        )
        self.assertIn("البركه", choice.store["storeName"])

    def test_outside_tolerance_prefers_discount(self):
        """Discounts outside 0.3% tolerance prefer higher discount."""
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
        self.assertEqual(_calculate_priority_score("البركه", preferred), 1)
        self.assertEqual(_calculate_priority_score("الريان", preferred), 2)
        self.assertEqual(_calculate_priority_score("غير معروف", preferred), 999)


class TestMaxAvailableMode(unittest.TestCase):
    """Test priority in max_available mode."""

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


def _store(name: str, qty: int, discount: float) -> dict:
    """Helper to create store dict."""
    return {
        "storeName": f"شركه {name}",
        "availableQuantity": qty,
        "retailPrice": 100.0,
        "salePrice": 100.0 * (1 - discount / 100),
        "storeProductId": f"id_{name}",
    }


if __name__ == "__main__":
    unittest.main()
