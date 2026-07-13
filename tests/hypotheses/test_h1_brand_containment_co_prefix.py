"""H1: Brand containment treats COAVAZIR as AVAZIR (len_diff=2, ratio~85.7).

Score this hypothesis by checking whether the brand checker currently accepts
the unsafe pair. High score means this hypothesis explains the production bug.
"""

from __future__ import annotations

import unittest

from rapidfuzz import fuzz

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_brand import (
    _brand_match_check,
)


class Hypothesis1BrandContainmentTests(unittest.TestCase):
    """Measure evidence for the brand-containment root cause."""

    def test_brand_metrics_match_artifact_path(self) -> None:
        d = parse_drug("CO_AVAZIR 5GM EYE OINTMENT")
        m = parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM")
        d_clean = "COAVAZIR"
        m_clean = "AVAZIR"
        self.assertEqual(d.brand.replace(" ", ""), d_clean)
        self.assertEqual(m.brand.replace(" ", ""), m_clean)
        self.assertTrue(m_clean in d_clean)
        self.assertEqual(abs(len(d_clean) - len(m_clean)), 2)
        self.assertGreaterEqual(fuzz.ratio(d_clean, m_clean), 82)
        self.assertLess(fuzz.ratio(d_clean, m_clean), 86)

    def test_current_brand_check_accepts_unsafe_pair_before_fix(self) -> None:
        """Before fix this documents the bug; after fix it should reject."""
        d = parse_drug("CO_AVAZIR 5GM EYE OINTMENT")
        m = parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM")
        ok, reason = _brand_match_check(d, m, brand_prefix_min=4)
        # After the fix this becomes False / different_brand.
        # The assertion below is the *desired* post-fix state used for scoring.
        self.assertFalse(ok)
        self.assertEqual(reason, "different_brand")


if __name__ == "__main__":
    unittest.main()
