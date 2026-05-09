"""Tests for product export deduplication."""

from __future__ import annotations

import unittest

from src.tawreed.product_export_deduplicator import (
    ProductIdentity,
    count_duplicates_removed,
    deduplicate_products,
    deduplicate_products_to_list,
    identity_key,
)


class ProductIdentityTests(unittest.TestCase):
    """Tests for ProductIdentity dataclass."""

    def test_identity_valid_when_all_fields_present(self) -> None:
        """Valid identity has all non-empty fields."""
        identity = ProductIdentity(
            product_name_en="Paracetamol 500mg",
            product_name_ar="باراسيتامول 500 ملغ",
            product_key="store:store-123",
        )
        self.assertTrue(identity.is_valid())

    def test_identity_invalid_when_english_empty(self) -> None:
        """Invalid when productNameEn is empty."""
        identity = ProductIdentity(
            product_name_en="",
            product_name_ar="باراسيتامول 500 ملغ",
            product_key="store:store-123",
        )
        self.assertFalse(identity.is_valid())

    def test_identity_invalid_when_arabic_empty(self) -> None:
        """Invalid when productName (Arabic) is empty."""
        identity = ProductIdentity(
            product_name_en="Paracetamol 500mg",
            product_name_ar="",
            product_key="store:store-123",
        )
        self.assertFalse(identity.is_valid())

    def test_identity_invalid_when_store_id_empty(self) -> None:
        """Invalid when storeProductId is empty."""
        identity = ProductIdentity(
            product_name_en="Paracetamol 500mg",
            product_name_ar="باراسيتامول 500 ملغ",
            product_key="",
        )
        self.assertFalse(identity.is_valid())

    def test_identity_invalid_when_whitespace_only(self) -> None:
        """Invalid when fields contain only whitespace."""
        identity = ProductIdentity(
            product_name_en="   ",
            product_name_ar="باراسيتامول 500 ملغ",
            product_key="store:store-123",
        )
        self.assertFalse(identity.is_valid())

    def test_identity_hashable_for_set_membership(self) -> None:
        """ProductIdentity is hashable and works in sets."""
        id1 = ProductIdentity("Panadol", "بنادول", "store-1")
        id2 = ProductIdentity("Panadol", "بنادول", "store-1")
        id3 = ProductIdentity("Panadol", "بنادول", "store-2")

        seen = {id1}
        self.assertIn(id2, seen)
        self.assertNotIn(id3, seen)


class IdentityKeyTests(unittest.TestCase):
    """Tests for identity_key extraction."""

    def test_identity_key_extracts_fields(self) -> None:
        """Extract identity key from product dict."""
        product = {
            "productNameEn": "Paracetamol 500mg",
            "productName": "باراسيتامول 500 ملغ",
            "storeProductId": "store-123",
        }
        key = identity_key(product)
        self.assertEqual(key.product_name_en, "Paracetamol 500mg")
        self.assertEqual(key.product_name_ar, "باراسيتامول 500 ملغ")
        self.assertEqual(key.product_key, "store:store-123")

    def test_identity_key_strips_whitespace(self) -> None:
        """Whitespace is stripped from extracted fields."""
        product = {
            "productNameEn": "  Paracetamol  ",
            "productName": "  باراسيتامول  ",
            "storeProductId": "  store-123  ",
        }
        key = identity_key(product)
        self.assertEqual(key.product_name_en, "Paracetamol")
        self.assertEqual(key.product_name_ar, "باراسيتامول")
        self.assertEqual(key.product_key, "store:store-123")

    def test_identity_key_handles_missing_fields(self) -> None:
        """Missing fields default to empty strings."""
        product = {}
        key = identity_key(product)
        self.assertEqual(key.product_name_en, "")
        self.assertEqual(key.product_name_ar, "")
        self.assertEqual(key.product_key, "")

    def test_identity_key_uses_product_id_when_store_product_id_missing(self) -> None:
        """Product id is the fallback identity for products without store id."""
        product = {
            "productNameEn": "ABIMOL 300 MG 5 RECTAL SUPP.",
            "productName": "ابيمول 300 مجم 5 لبوس",
            "productId": 34,
            "storeProductId": None,
        }
        key = identity_key(product)
        self.assertEqual(key.product_key, "product:34")


class DeduplicateProductsTests(unittest.TestCase):
    """Tests for product deduplication."""

    def test_deduplicator_removes_exact_duplicates(self) -> None:
        """Identical products are deduplicated."""
        products = [
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
                "salePrice": 10.0,
            },
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
                "salePrice": 10.0,
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 1)

    def test_deduplicator_preserves_first_occurrence(self) -> None:
        """First occurrence is kept, later duplicates removed."""
        products = [
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
                "salePrice": 10.0,
            },
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
                "salePrice": 15.0,  # Different price
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["salePrice"], 10.0)

    def test_deduplicator_keeps_different_store_ids(self) -> None:
        """Products with different storeProductIds are kept."""
        products = [
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
            },
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-2",
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 2)

    def test_deduplicator_keeps_different_english_names(self) -> None:
        """Products with different English names are kept."""
        products = [
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
            },
            {
                "productNameEn": "Panadol Extra",
                "productName": "بنادول",
                "storeProductId": "store-1",
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 2)

    def test_deduplicator_skips_null_identity_products(self) -> None:
        """Products with empty identity fields are skipped."""
        products = [
            {
                "productNameEn": "Panadol",
                "productName": "بنادول",
                "storeProductId": "store-1",
            },
            {
                "productNameEn": "",  # Empty English name
                "productName": "بنادول",
                "storeProductId": "store-2",
            },
            {
                "productNameEn": "Aspirin",
                "productName": "أسبرين",
                "storeProductId": "store-3",
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 2)
        names = [p["productNameEn"] for p in result]
        self.assertIn("Panadol", names)
        self.assertIn("Aspirin", names)

    def test_deduplicator_keeps_products_with_product_id_only(self) -> None:
        """Products with productId but no storeProductId are exported."""
        products = [
            {
                "productId": 34,
                "productNameEn": "ABIMOL 300 MG 5 RECTAL SUPP.",
                "productName": "ابيمول 300 مجم 5 لبوس",
                "storeProductId": None,
            },
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["productId"], 34)

    def test_deduplicator_preserves_order(self) -> None:
        """Deduplication preserves input order."""
        products = [
            {"productNameEn": "A", "productName": "أ", "storeProductId": "1"},
            {"productNameEn": "B", "productName": "ب", "storeProductId": "2"},
            {"productNameEn": "C", "productName": "ج", "storeProductId": "3"},
        ]
        result = deduplicate_products_to_list(products)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["productNameEn"], "A")
        self.assertEqual(result[1]["productNameEn"], "B")
        self.assertEqual(result[2]["productNameEn"], "C")

    def test_deduplicator_handles_empty_list(self) -> None:
        """Empty list returns empty."""
        result = deduplicate_products_to_list([])
        self.assertEqual(len(result), 0)

    def test_deduplicator_is_generator(self) -> None:
        """deduplicate_products returns an iterator."""
        products = [
            {"productNameEn": "A", "productName": "أ", "storeProductId": "1"},
        ]
        result = deduplicate_products(products)
        self.assertTrue(hasattr(result, "__iter__"))
        self.assertTrue(hasattr(result, "__next__"))


class CountDuplicatesRemovedTests(unittest.TestCase):
    """Tests for duplicate count calculation."""

    def test_count_duplicates_removed(self) -> None:
        """Calculate correct number of duplicates removed."""
        self.assertEqual(count_duplicates_removed(100, 95), 5)

    def test_count_duplicates_removed_zero(self) -> None:
        """No duplicates removed when counts are equal."""
        self.assertEqual(count_duplicates_removed(50, 50), 0)

    def test_count_duplicates_removed_handles_negative(self) -> None:
        """Return 0 for invalid cases (deduplicated > original)."""
        self.assertEqual(count_duplicates_removed(50, 100), 0)


if __name__ == "__main__":
    unittest.main()
