import unittest

from src.core.matching.search_query_templates import category_queries


class SearchQueryTemplatesTests(unittest.TestCase):
    """Validate category-aware query template generation."""

    def test_liquids_generation(self) -> None:
        """Brufen syrup should generate brand + volume and brand + dosage first."""
        queries = category_queries("BRUFEN SYRUP 100MG/5ML 120ML")
        self.assertIn("BRUFEN 120", queries)
        self.assertIn("BRUFEN 100MG/ML", queries)

    def test_injections_generation(self) -> None:
        """Clexane syringe/ampoule should generate brand + dosage + form first."""
        queries = category_queries("CLEXANE 40MG AMP")
        self.assertIn("CLEXANE 40MG AMP", queries)
        self.assertIn("CLEXANE 40MG", queries)

    def test_tablets_generation_empty(self) -> None:
        """Panadol tablets should return empty category queries (falling back to default)."""
        queries = category_queries("PANADOL 500MG TABS")
        self.assertEqual(queries, [])
