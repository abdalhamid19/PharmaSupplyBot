import unittest

from src.core.utils.excel import Item
from src.core.product_matching import _search_queries_for_item


class ProductMatchingQueryTests(unittest.TestCase):
    def test_search_queries_include_normalized_dosage_variants(self) -> None:
        item = Item(code="92037", name="QUINSTIBOWL 5MG 20F.C TABS", qty=3)

        queries = _search_queries_for_item(item)

        self.assertIn("QUINSTIBOWL 5MG 20F.C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20 F C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20", queries)
        self.assertEqual(queries[-1], "QUINSTIBOWL")


if __name__ == "__main__":
    unittest.main()
