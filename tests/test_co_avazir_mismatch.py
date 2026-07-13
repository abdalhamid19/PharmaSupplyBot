"""Regression tests for CO_AVAZIR matching AVAZIR (wrong product).

Problem (item 80838):
  Query:    CO_AVAZIR 5GM EYE OINTMENT
  Wrong:    AVAZIR 0.3 % EYE OINT. 5 GM   (accepted today)
  Correct:  CO AVAZIR EYE OINT. 5 GM      (should win when orderable)

These tests fail before the fix and pass after it.
"""

from __future__ import annotations

import unittest

from src.core.drug_matching.normalization.normalizer import parse_drug
from src.core.drug_matching.normalization.normalizer_matching_core import (
    components_match,
)
from src.core.matching.product_matching import explain_best_product_match
from src.core.utils.excel import Item


def _candidate(
    english_name: str,
    *,
    store_id: str | None = "store-1",
    arabic_name: str = "",
    available: int = 5,
) -> dict[str, object]:
    """Build one Tawreed-style candidate dict for matching tests."""
    row: dict[str, object] = {
        "productNameEn": english_name,
        "productName": arabic_name,
        "availableQuantity": available,
        "productsCount": available,
    }
    if store_id is not None:
        row["storeProductId"] = store_id
    return row


class CoAvazirMismatchReproductionTests(unittest.TestCase):
    """Prove the production bug before any fix is applied."""

    ITEM = Item(code="80838", name="CO_AVAZIR 5GM EYE OINTMENT", qty=1)
    WRONG = "AVAZIR 0.3 % EYE OINT. 5 GM"
    CORRECT = "CO AVAZIR EYE OINT. 5 GM"

    def test_brand_check_rejects_avazir_for_co_avazir(self) -> None:
        """COAVAZIR and AVAZIR are different brand lines in Tawreed catalog."""
        ok, reason = components_match(parse_drug(self.ITEM.name), parse_drug(self.WRONG))
        self.assertFalse(ok, "CO_AVAZIR must not brand-match plain AVAZIR")
        self.assertEqual(reason, "different_brand")

    def test_wrong_candidate_alone_is_not_accepted(self) -> None:
        """Even when only AVAZIR ointment is returned, it must not win."""
        decision = explain_best_product_match(
            self.ITEM,
            [(self.ITEM.name, [_candidate(self.WRONG, store_id="1450")])],
        )
        self.assertIsNone(
            decision.best_match,
            f"wrong product accepted: {decision.final_reason}",
        )

    def test_correct_orderable_candidate_is_accepted(self) -> None:
        """Correct CO AVAZIR ointment must match when storeProductId exists."""
        decision = explain_best_product_match(
            self.ITEM,
            [(self.ITEM.name, [_candidate(self.CORRECT, store_id="3386")])],
        )
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], self.CORRECT)

    def test_correct_beats_wrong_when_both_orderable(self) -> None:
        """When both products are orderable, CO AVAZIR must beat AVAZIR."""
        decision = explain_best_product_match(
            self.ITEM,
            [
                (
                    self.ITEM.name,
                    [
                        _candidate(self.WRONG, store_id="1450"),
                        _candidate(self.CORRECT, store_id="3386"),
                    ],
                )
            ],
        )
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], self.CORRECT)

    def test_production_shape_wrong_not_chosen_over_unorderable_correct(self) -> None:
        """Mirror production: correct lacks storeProductId; wrong must still lose."""
        decision = explain_best_product_match(
            self.ITEM,
            [
                (
                    self.ITEM.name,
                    [
                        _candidate(self.CORRECT, store_id=None, available=0),
                        _candidate(self.WRONG, store_id="2145446", available=7),
                    ],
                )
            ],
        )
        if decision.best_match is not None:
            self.assertNotEqual(
                decision.best_match.data["productNameEn"],
                self.WRONG,
                "must not substitute unorderable CO AVAZIR with AVAZIR",
            )


if __name__ == "__main__":
    unittest.main()
