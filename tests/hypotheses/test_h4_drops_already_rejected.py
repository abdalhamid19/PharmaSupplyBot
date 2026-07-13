"""H4: AVAZIR eye drops are already rejected (not this bug).

Previous fix put OINT before EYE in FORM_SCAN_ORDER, so drops vs ointment
already returns different_form. The live bug is ointment-vs-ointment.
"""

from __future__ import annotations

import unittest

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)
from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class Hypothesis4DropsAlreadyRejectedTests(unittest.TestCase):
    """Disprove that the live wrong match is the drops candidate."""

    def test_eye_drops_rejected_before_acceptance(self) -> None:
        ok, reason = components_match(
            parse_drug("CO_AVAZIR 5GM EYE OINTMENT"),
            parse_drug("AVAZIR 0.3 % EYE DROPS 10 ML"),
        )
        self.assertFalse(ok)
        # Brand check runs before form; COAVAZIR vs AVAZIR already rejects.
        self.assertIn(reason, {"different_brand", "different_form"})

    def test_eye_drops_not_accepted_as_best_match(self) -> None:
        item = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
        drops = {
            "productNameEn": "AVAZIR 0.3 % EYE DROPS 10 ML",
            "productName": "x",
            "storeProductId": "1449",
            "availableQuantity": 5,
        }
        decision = explain_best_product_match(item, [(item.name, [drops])])
        self.assertIsNone(decision.best_match)


if __name__ == "__main__":
    unittest.main()
