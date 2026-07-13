"""H3: Wrong product passes form/numeric gates (not the primary brand bug).

AVAZIR ointment shares form OINT and 5 GM; 0.3% is treated as safe omission.
This enables acceptance AFTER brand check wrongly passes.
"""

from __future__ import annotations

import unittest

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)
from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Hypothesis3SafeOmissionAndFormTests(unittest.TestCase):
    """Confirm form/numeric path is permissive once brand is accepted."""

    def test_same_form_oint_for_both_products(self) -> None:
        requested = parse_drug("CO_AVAZIR 5GM EYE OINTMENT")
        wrong = parse_drug("AVAZIR 0.3 % EYE OINT. 5 GM")
        correct = parse_drug("CO AVAZIR EYE OINT. 5 GM")
        self.assertEqual(requested.form, "OINT")
        self.assertEqual(wrong.form, "OINT")
        self.assertEqual(correct.form, "OINT")

    def test_wrong_product_acceptance_reason_is_safe_omission_when_brand_passes(
        self,
    ) -> None:
        """Documents pre-fix path; post-fix wrong product is rejected earlier."""
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        wrong = {
            "productNameEn": "AVAZIR 0.3 % EYE OINT. 5 GM",
            "productName": "x",
            "storeProductId": "1450",
            "availableQuantity": 7,
        }
        decision = explain_best_product_match(item, [(item.name, [wrong])])
        # Desired: no match (brand rejected). If still matched, reason was safe omission.
        if decision.best_match is not None:
            self.assertIn("safe omission", decision.final_reason.lower())
        else:
            ok, reason = components_match(
                parse_drug(item.name),
                parse_drug(wrong["productNameEn"]),
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "different_brand")


if __name__ == "__main__":
    unittest.main()
