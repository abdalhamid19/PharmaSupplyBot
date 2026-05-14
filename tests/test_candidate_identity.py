import unittest

from src.core.candidate_identity import (
    candidate_has_store_product_id,
    candidate_store_product_id,
)


class CandidateIdentityTests(unittest.TestCase):
    def test_store_product_id_is_preferred(self) -> None:
        candidate = {"storeProductId": 1460790, "id": 12}

        self.assertEqual(candidate_store_product_id(candidate), "1460790")

    def test_snake_case_id_is_supported(self) -> None:
        candidate = {"store_product_id": "2695415"}

        self.assertEqual(candidate_store_product_id(candidate), "2695415")

    def test_product_store_id_alias_is_supported(self) -> None:
        candidate = {"productStoreId": "2341067.0"}

        self.assertEqual(candidate_store_product_id(candidate), "2341067")

    def test_nested_metadata_store_id_is_supported(self) -> None:
        candidate = {"metadata": {"storeProductId": "nested-1"}}

        self.assertEqual(candidate_store_product_id(candidate), "nested-1")

    def test_plain_id_is_not_orderable(self) -> None:
        candidate = {"id": "2341067.0"}

        self.assertEqual(candidate_store_product_id(candidate), "")
        self.assertFalse(candidate_has_store_product_id(candidate))

    def test_empty_values_are_not_orderable(self) -> None:
        for value in ("", None, "None", "nan", "null"):
            with self.subTest(value=value):
                self.assertEqual(candidate_store_product_id({"storeProductId": value}), "")
                self.assertFalse(candidate_has_store_product_id({"storeProductId": value}))


if __name__ == "__main__":
    unittest.main()
