"""Regression fixtures from the 20260514_1852 no-results audit."""

from __future__ import annotations

import unittest

from src.core.product_matching import explain_best_product_match
from src.core.utils.excel import Item


class LatestNoResultsRegressionTests(unittest.TestCase):
    """Lock down high-signal false negatives from the latest order run."""

    def test_latest_safe_false_negatives_become_matches(self) -> None:
        cases = [
            ("26979", "IVERZINE LOTION 6O ML", "IVERZINE 1 % LOTION 60 ML"),
            ("83061", "CLOSOL 50 ML SPRAY", "CLOSOL 10 MG / ML TOPICAL SPRAY 50 ML"),
            (
                "73173",
                "CONCOR 5 PLUS 30TAB",
                "CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS",
            ),
            (
                "89588",
                "REXODIN 10% ANTISEPTIC SOLUTION 60 ML",
                "REXODIN ANTISEPTIC SOLUTION 60 ML",
            ),
            ("73267", "VITACID C EFF 12 TAB", "VITACID C 1 GM 12 EFF TAB"),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id=f"s-{code}")])],
                )
                self.assertIsNotNone(decision.best_match)

    def test_latest_non_orderable_rows_do_not_become_actionable_matches(self) -> None:
        cases = [
            (
                "57680",
                "POTASSIUM CHLORIDE 5 ML",
                "POTASSIUM CHLORIDE I.V. 5 ML 5 AMP",
            ),
            ("16763", "AMRIZOLE N SUPP", "AMRIZOLE N 5 VAG. SUPP."),
            ("61862", "AMLODIPINE 5MG 30 TAB", "AMLODIPINE 5 MG 30 TAB."),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id="")])],
                )
                self.assertIsNone(decision.best_match)
                self.assertIn("storeProductId", decision.final_reason)

    def test_latest_unsafe_missing_strength_still_requires_review(self) -> None:
        decision = explain_best_product_match(
            Item(code="74881", name="OCTOZINC CAP", qty=1),
            [("OCTOZINC CAP", [_candidate("OCTOZINC 25 MG 20 CAPS.")])],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("unrequested numeric token", decision.final_reason)

    # -- Phase 1: canonical dosage model & numeric safety regressions --

    def test_phase1_pack_count_safe_when_dosage_matches(self) -> None:
        """Extra pack count should not block when the strength already matches."""
        cases = [
            ("BRUFEN 400 TAB", "BRUFEN 400 MG 30 TABS."),
            ("NEXIUM 20 MG", "NEXIUM 20 MG 14 CAPS."),
            ("E-MOX 500MG CAP", "E MOX 500 MG 16 CAPS."),
        ]
        for item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code="p1", name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id="s-p1")])],
                )
                self.assertIsNotNone(decision.best_match)

    def test_phase1_liquid_concentration_volume_safe(self) -> None:
        """Per-ML concentration and total volume should not block when
        strength matches."""
        decision = explain_best_product_match(
            Item(code="p1", name="AUGMENTIN 457 SUSP", qty=1),
            [("AUGMENTIN 457 SUSP", [
                _candidate("AUGMENTIN 457 MG / 5 ML SUSP 80 ML", store_id="s-p1"),
            ])],
        )
        self.assertIsNotNone(decision.best_match)

    def test_phase1_injection_missing_strength_still_requires_review(self) -> None:
        """An injection whose query omits strength must NOT auto-match."""
        decision = explain_best_product_match(
            Item(code="p1", name="ADWIFLAM 6 AMP", qty=1),
            [("ADWIFLAM 6 AMP", [
                _candidate("ADWIFLAM 75 MG / 3 ML 6 AMP.", store_id="s-p1"),
            ])],
        )
        self.assertIsNone(decision.best_match)

    def test_phase1_missing_strength_with_pack_still_requires_review(self) -> None:
        """Missing strength + pack count must NOT auto-match."""
        decision = explain_best_product_match(
            Item(code="p1", name="OCTOZINC CAP", qty=1),
            [("OCTOZINC CAP", [_candidate("OCTOZINC 25 MG 20 CAPS.")])],
        )
        self.assertIsNone(decision.best_match)


def _candidate(english_name: str, store_id: str = "store-1") -> dict[str, object]:
    """Return one Tawreed-style candidate for regression tests."""
    candidate = {
        "productNameEn": english_name,
        "productName": "",
        "availableQuantity": 5,
        "productsCount": 5,
    }
    if store_id:
        candidate["storeProductId"] = store_id
    return candidate


if __name__ == "__main__":
    unittest.main()
