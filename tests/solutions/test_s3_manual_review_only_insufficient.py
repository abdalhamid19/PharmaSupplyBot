"""S3 scoring: relying only on manual review / stock data is insufficient.

Even if correct product later gains storeProductId, brand check must still
block AVAZIR when user asked for CO_AVAZIR. Manual-only is not a root fix.
"""

from __future__ import annotations

import unittest

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)


class Solution3ManualReviewOnlyTests(unittest.TestCase):
    """Show brand safety must not depend on inventory/orderability alone."""

    def test_brand_rejection_independent_of_store_id(self) -> None:
        ok, reason = components_match(
            parse_drug("CO_AVAZIR 5GM EYE OINTMENT"),
            parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM"),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "different_brand")


if __name__ == "__main__":
    unittest.main()
