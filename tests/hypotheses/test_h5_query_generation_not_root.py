"""H5: Query generation is not the root cause.

Search queries include CO AVAZIR variants; the correct product is found in API
results (artifacts rank it #1 by score). Failure is acceptance/selection.
"""

from __future__ import annotations

import unittest

from src.core.matching.product_matching_queries import search_queries_for_item
from src.core.utils.excel import Item


class Hypothesis5QueryGenerationTests(unittest.TestCase):
    """Show queries already cover the correct product name family."""

    def test_queries_include_co_avazir_variants(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        queries = search_queries_for_item(item)
        joined = " | ".join(queries).upper()
        self.assertIn("CO AVAZIR", joined)
        self.assertTrue(any("OINT" in q.upper() for q in queries))


if __name__ == "__main__":
    unittest.main()
