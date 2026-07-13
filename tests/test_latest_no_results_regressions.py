"""Regression fixtures from the 20260514_1852 no-results audit."""

from __future__ import annotations

import unittest

from src.core.matching.product_matching import explain_best_product_match
from src.core.config.config_models import MatchingConfig
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

    # -- Phase 2: component/brand matching regressions --

    def test_phase2_form_words_not_absorbed_into_brand(self) -> None:
        """SUSPENSION, EMULSION, ENEMA should be form boundaries, not brand."""
        cases = [
            ("DOLO D SUSPENSION 115 ML", "DOLO D ORAL SUSP. 115 ML"),
            ("ENEMAX 120ML VIAL", "ENEMAX ENEMA 120 ML"),
            ("SIMEDILL SYRUP 120ML", "SIMEDILL EMULSION 120 ML"),
        ]
        for item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code="p2", name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id="s-p2")])],
                )
                self.assertIsNotNone(decision.best_match)

    def test_phase2_supplement_descriptor_not_in_brand(self) -> None:
        """CALCIUM after brand name should be a descriptor, not part of brand."""
        decision = explain_best_product_match(
            Item(code="p2", name="TOTACAL CALCIUM 30 TAB", qty=1),
            [("TOTACAL CALCIUM 30 TAB", [
                _candidate("TOTACAL 30 TABS", store_id="s-p2"),
            ])],
        )
        self.assertIsNotNone(decision.best_match)

    def test_phase2_retard_sr_modifier_equivalence(self) -> None:
        """RETARD and SR are equivalent release modifiers."""
        decision = explain_best_product_match(
            Item(code="p2", name="EPILAT RETARD 20 TAB", qty=1),
            [("EPILAT RETARD 20 TAB", [
                _candidate("EPILAT RETARD 20 MG SR. 20 F.C.TAB.", store_id="s-p2"),
            ])],
        )
        self.assertIsNotNone(decision.best_match)

    def test_phase2_milk_noise_word_not_in_brand(self) -> None:
        """MILK should not be absorbed into the brand."""
        decision = explain_best_product_match(
            Item(code="p2", name="HERO BABY FEH 400 GM", qty=1),
            [("HERO BABY FEH 400 GM", [
                _candidate("HERO BABY FEH MILK 400 GM", store_id="s-p2"),
            ])],
        )
        self.assertIsNotNone(decision.best_match)

    def test_phase2_different_modifiers_still_rejected(self) -> None:
        """PANADOL JOINT != PANADOL COLD FLU DAY (different modifiers)."""
        decision = explain_best_product_match(
            Item(code="p2", name="PANADOL JOINT 24 TABS", qty=1),
            [("PANADOL JOINT 24 TABS", [
                _candidate("PANADOL COLD FLU DAY 24 F.C. TABS.", store_id="s-p2"),
            ])],
        )
        self.assertIsNone(decision.best_match)

    # -- Phase 3: identity token & spelling tolerance regressions --

    def test_phase3_fuzzy_identity_tokens_tolerate_typos(self) -> None:
        """1-2 char typos in brand names should not block identity check."""
        cases = [
            ("AMEBAZOLE 1 GM 2 TAB", "AMEBAZOL 1 GM 2 F.C. TABS."),
            ("PROCORLAN 7.5MG TAB", "PROCORALAN 7.5 MG 28 F.C. TABS."),
            ("ZADOGLOBN 20 CAPS", "ZADOGLOBIN 20 CAPS"),
            ("MONONDEXIN 0.1 EYE DROPS", "MONODEXIN 0.1 % EYE DROPS 10 ML"),
        ]
        for item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code="p3", name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id="s-p3")])],
                )
                self.assertIsNotNone(decision.best_match)

    def test_phase3_units_normalized_to_iu(self) -> None:
        """'UNITS' should be normalized to 'IU' for dosage parsing."""
        from src.core.drug_matching.normalization.normalizer import parse_drug, components_match
        r = parse_drug("LANTUS 100 UNITS 5 CARTRIDGES")
        o = parse_drug("LANTUS 100 I.U. / ML 5 CARTRIDGES")
        compat, _ = components_match(r, o)
        self.assertTrue(compat)

    def test_methyl_folate_orchidia_candidate_beats_ora(self) -> None:
        """ORCHIDIA candidate must win; ORA must not be auto-selected."""
        item = Item(code="83165", name="METHYL FOLATE 30 CAP ORCHIDIA", qty=1)
        decision = explain_best_product_match(
            item,
            [(item.name, [
                _candidate("METHYL FOLATE (ORCHIDIA) 30 CAPS", store_id="orchidia"),
                _candidate("METHYL FOLATE ORA 30 CAPS", store_id="ora"),
            ])],
            matching_config=MatchingConfig(reject_extra_brand_token=True),
        )

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"],
            "METHYL FOLATE (ORCHIDIA) 30 CAPS",
        )

    def test_bebelac_lf_does_not_become_no_results_when_lf_candidate_exists(self) -> None:
        """LF formula candidate should remain matchable; FL is an accepted typo of LF."""
        item = Item(code="30089", name="BEBELAC LF MILK", qty=1)
        decision = explain_best_product_match(
            item,
            [(item.name, [
                _candidate("BEBELAC LF MILK 400 GM", store_id="lf"),
                _candidate("BEBELAC FL MILK 400 GM", store_id="fl"),
            ])],
            matching_config=MatchingConfig(reject_extra_brand_token=True),
        )

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], "BEBELAC LF MILK 400 GM")

    def test_bebelac_lf_matches_fl_candidate_when_lf_absent(self) -> None:
        """LF query must match FL-only candidate (LF/FL are interchangeable baby formula typos)."""
        item = Item(code="30089", name="BEBELAC LF MILK", qty=1)
        decision = explain_best_product_match(
            item,
            [(item.name, [_candidate("BEBELAC FL MILK 400 GM", store_id="fl")])],
            matching_config=MatchingConfig(reject_extra_brand_token=True),
        )

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], "BEBELAC FL MILK 400 GM")

    def test_reported_wrong_matches_are_rejected(self) -> None:
        """Lock down reported unsafe product substitutions from July audit."""
        cases = [
            ("92558", "LIMITLESS MILGA MAX 30 TABS", "LIMITLESS MAN MAX 30 TABS"),
            ("77101", "GARAMYCIN OINT 15GM", "GARAMYCIN 0.1 % CREAM 15 GM"),
            ("34157", "DIPROSONE OINT", "DIPROSONE 0.05 % CREAM 30 GM"),
            ("80838", "CO_AVAZIR 5GM EYE OINTMENT", "AVAZIR 0.3 % EYE DROPS 10 ML"),
            ("79407", "LILI FEMININE WASH 250ML", "LILIOX 10 SACHETS"),
            ("58580", "ISIS CINNAMON WITH GINGER 20 BAG", "ISIS CINNAMON 20 FILTER BAGS"),
            ("74096", "CAL MAG 30TAB", "CAL MAG JOINT 30 TAB"),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id=f"s-{code}")])],
                )
                self.assertIsNone(decision.best_match)

    def test_reported_correct_matches_are_accepted(self) -> None:
        """Ensure the corrected alternatives do not regress to no-results."""
        cases = [
            ("77101", "GARAMYCIN OINT 15GM", "GARAMYCIN 0.1 % OINT. 15 GM"),
            ("34157", "DIPROSONE OINT", "DIPROSONE 0.05 % OINT. 10 GM"),
            (
                "58580",
                "ISIS CINNAMON WITH GINGER 20 BAG",
                "ISIS GINGER CINNAMON 20 FILTER BAGS",
            ),
            ("74096", "CAL MAG 30TAB", "CAL MAG 30 F.C. TABLETS"),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [_candidate(candidate_name, store_id=f"s-{code}")])],
                )
                self.assertIsNotNone(decision.best_match)
                self.assertEqual(decision.best_match.data["productNameEn"], candidate_name)

    def test_cal_mag_prefers_plain_over_joint(self) -> None:
        """CAL MAG 30TAB must choose plain tablets, never the JOINT variant."""
        item = Item(code="74096", name="CAL MAG 30TAB", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _candidate("CAL MAG JOINT 30 TAB", store_id="2144187"),
                        _candidate("CAL MAG 30 F.C. TABLETS", store_id="2288836"),
                    ],
                )
            ],
        )
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"],
            "CAL MAG 30 F.C. TABLETS",
        )

    def test_cal_mag_joint_query_still_matches_joint(self) -> None:
        """Explicit JOINT queries must still match the JOINT SKU."""
        item = Item(code="84407", name="CAL MAG JOINT 30TAB", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _candidate("CAL MAG JOINT 30 TAB", store_id="2144187"),
                        _candidate("CAL MAG 30 F.C. TABLETS", store_id="2288836"),
                    ],
                )
            ],
        )
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"],
            "CAL MAG JOINT 30 TAB",
        )


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
