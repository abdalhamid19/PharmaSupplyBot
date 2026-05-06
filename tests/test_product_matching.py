import unittest

from src.core.product_matching import _search_queries_for_item
from src.core.utils.excel import Item


class ProductMatchingQueryTests(unittest.TestCase):
    def test_search_queries_include_normalized_dosage_variants(self) -> None:
        item = Item(code="92037", name="QUINSTIBOWL 5MG 20F.C TABS", qty=3)

        queries = _search_queries_for_item(item)

        self.assertIn("QUINSTIBOWL 5MG 20F.C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20 F C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20", queries)
        self.assertIn("92037", queries)
        self.assertIn("5 MG", queries)
        self.assertIn("F", queries)
        self.assertLessEqual(len(queries), 24)

    def test_short_names_include_code_fallback_after_unique_variants(self) -> None:
        item = Item(code="73368", name="KENACOMB CREAM", qty=1)

        queries = _search_queries_for_item(item)

        self.assertGreaterEqual(len(queries), 4)
        self.assertIn("73368", queries)
        self.assertIn("CREAM", queries)


if __name__ == "__main__":
    unittest.main()
