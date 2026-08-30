"""Tests for store-level identity keys used by order-run persistence."""

from __future__ import annotations

import unittest

from src.core.ordering.store_identity import store_identity_key


class StoreIdentityKeyTests(unittest.TestCase):
    """Validate that store identity is never derived from product-level ids."""

    def test_prefers_store_id_over_store_product_id(self) -> None:
        """storeProductId identifies a product-in-store, not a store."""
        row = {"storeProductId": 2902379, "storeId": 55, "storeName": "X"}
        self.assertEqual(store_identity_key(row), "storeId:55")

    def test_ignores_store_product_id_completely(self) -> None:
        """A row with only storeProductId falls back to the store name."""
        name = "شركه العاصمه (الجيزه)"
        row = {"storeProductId": 2902379, "storeName": name}
        self.assertEqual(store_identity_key(row), f"storeName:{name}")

    def test_falls_back_through_supplier_and_warehouse_ids(self) -> None:
        """Supplier and warehouse ids are valid store-level identities."""
        self.assertEqual(store_identity_key({"supplierId": 7}), "supplierId:7")
        self.assertEqual(store_identity_key({"warehouseId": 9}), "warehouseId:9")

    def test_uses_normalized_store_name_when_no_id_exists(self) -> None:
        """Collapsed whitespace keeps the same store stable across runs."""
        row = {"storeName": "  شركه   البركه  "}
        self.assertEqual(store_identity_key(row), "storeName:شركه البركه")

    def test_reads_nested_store_objects(self) -> None:
        """Nested store payloads still resolve to a store identity."""
        row = {"store": {"id": 12, "name": "شركه الماسه"}}
        self.assertEqual(store_identity_key(row), "storeName:شركه الماسه")

    def test_returns_empty_for_unidentifiable_row(self) -> None:
        """An empty identity signals the caller to skip the row."""
        self.assertEqual(store_identity_key({}), "")
        self.assertEqual(store_identity_key({"storeName": "  "}), "")

    def test_normalizes_float_like_ids(self) -> None:
        """Excel-sourced ids arrive as 55.0 and must not fork the dimension."""
        self.assertEqual(store_identity_key({"storeId": "55.0"}), "storeId:55")

    def test_treats_placeholder_ids_as_missing(self) -> None:
        """Literal none/nan/null values are not usable identities."""
        row = {"storeId": "None", "supplierId": "nan", "storeName": "شركه الريان"}
        self.assertEqual(store_identity_key(row), "storeName:شركه الريان")

    def test_is_stable_across_calls(self) -> None:
        """The same payload always produces the same key."""
        row = {"storeId": 55}
        self.assertEqual(store_identity_key(row), store_identity_key(dict(row)))


if __name__ == "__main__":
    unittest.main()
