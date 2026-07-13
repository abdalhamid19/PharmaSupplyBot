"""S2 scoring: raise containment len_diff==2 threshold from 82 to 86.

This alone also rejects COAVAZIR/AVAZIR (ratio ~85.7). Documented as secondary
defense already applied together with S1.
"""

from __future__ import annotations

import unittest

from rapidfuzz import fuzz

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)


class Solution2ContainmentThresholdTests(unittest.TestCase):
    """Confirm tightened containment threshold covers the reported pair."""

    def test_ratio_is_between_old_and_new_threshold(self) -> None:
        ratio = fuzz.ratio("COAVAZIR", "AVAZIR")
        self.assertGreaterEqual(ratio, 82)
        self.assertLess(ratio, 86)

    def test_pair_rejected_after_threshold_change(self) -> None:
        ok, reason = components_match(
            parse_drug("CO_AVAZIR 5GM EYE OINTMENT"),
            parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM"),
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "different_brand")


if __name__ == "__main__":
    unittest.main()
