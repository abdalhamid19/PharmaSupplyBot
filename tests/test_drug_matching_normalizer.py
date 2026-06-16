from __future__ import annotations

import unittest

from src.core.drug_matching.normalizer import (
    components_match, normalize, normalize_arabic, parse_drug,
)


class NormalizerTests(unittest.TestCase):
    def test_normalize_handles_noise_compact_tokens_and_decimals(self) -> None:
        cases = [
            ("+***IMP PANADOL20MG 30TAB", "PANADOL 20 MG 30 TAB"),
            ("+***imp PANADOL NIGHT 20 TAB", "PANADOL NIGHT 20 TAB"),
            ("INDERAL 10MG 50TAB", "INDERAL 10 MG 50 TAB"),
            ("OMEPRAZOLE 21-CAP", "OMEPRAZOLE 21 CAP"),
            ("GYNOCONAZOLE 0.8% CREAM", "GYNOCONAZOLE 0.8% CREAM"),
            ("VITAMIN D 1.000IU", "VITAMIN D 1000 IU"),
            ("FEROGLOBIN B12 30 CAP", "FEROGLOBIN B12 30 CAP"),
            ("CALCIUM D3 30 TAB", "CALCIUM D3 30 TAB"),
            ("PANADOL EXTRA 24 TAB IMP", "PANADOL EXTRA 24 TAB IMP"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw), expected)

    def test_normalize_arabic_unifies_common_letters(self) -> None:
        cases = [
            ("إيزوميبرازول ٤٠ مجم", "ايزوميبرازول ٤٠ مجم"),
            ("كبسولة", "كبسوله"),
            ("على", "علي"),
            ("أقراص", "اقراص"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_arabic(raw), expected)

    def test_parse_drug_extracts_core_components(self) -> None:
        comp = parse_drug("+***IMP AUGMENTIN625MG 10TABS")

        self.assertEqual(comp.brand, "AUGMENTIN")
        self.assertEqual(comp.dosage_nums, ("625",))
        self.assertEqual(comp.dosage_units, ("MG",))
        self.assertEqual(comp.qty, "10")
        self.assertTrue(comp.imported)
        self.assertEqual(comp.normalized, "AUGMENTIN 625 MG 10 TABS")

    def test_parse_drug_builds_brand_variants_for_descriptors(self) -> None:
        comp = parse_drug("+***imp PANADOL COLD AND FLU TAB")

        self.assertEqual(comp.brand, "PANADOL")
        self.assertIn("PANADOL", comp.brand_variants)
        self.assertIn("PANADOLCOLD", comp.brand_variants)

    def test_parse_drug_classifies_non_medicine_products(self) -> None:
        cases = [
            ("DERMA ACTIVE BODY MILK 200 ML", "cosmetic"),
            ("CERELAC WHEAT AND MILK 125 GM", "baby_food"),
            ("DUREX REAL FEEL 3 CONDOMS", "device"),
            ("BIOTIN 10000 MCG 100 TAB", "supplement"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(parse_drug(raw).product_class, expected)

    def test_parse_drug_detects_compact_import_prefix(self) -> None:
        comp = parse_drug("+***IMPGlUCOSAMINE CHONDROTN MSM 120CAP")

        self.assertTrue(comp.imported)

    def test_parse_drug_separates_packaging_weight_from_dosage(self) -> None:
        comp = parse_drug("PRODUCT 500 MG 30 TAB 20 GM")

        self.assertEqual(comp.dosage_nums, ("500",))
        self.assertEqual(comp.dosage_units, ("MG",))
        self.assertEqual(comp.qty, "30")
        self.assertEqual(comp.weight, "20")

    def test_parse_drug_extracts_capsules_quantity(self) -> None:
        comp = parse_drug("AIG ESOMEPRAZOLE 40 MG 28 CAPSULES 2 STRIPS")

        self.assertEqual(comp.brand, "AIG")
        self.assertEqual(comp.dosage_nums, ("40",))
        self.assertEqual(comp.qty, "28")

    def test_parse_drug_ignores_descriptors_in_brand(self) -> None:
        cases = [
            ("ALPHANOVA OPHTALMIC SOLUTION 5 ML", "ALPHANOVA"),
            ("ALPHANOVA PLUS OPHTALMIC SOLUTION 5 ML", "ALPHANOVAPLUS"),
            ("ALOEKITA HAIR GROWTH SPRAY 200 ML", "ALOEKITA"),
            ("ALOEKITA CAFFEINE RICH DS DA SHAMPOO 250 ML", "ALOEKITA"),
            ("ALKA MISR ALKALINE WASH POWDER 12 SACHETS", "ALKAMISR"),
            ("AMIKACIN AMOUN 500 MG / 2 ML VIAL", "AMIKACIN"),
            ("ASPOCID INF 30TAB", "ASPOCID"),
            ("ASPOCID PAEDIATRIC 75 MG 30 CHEWABLE TAB", "ASPOCID"),
            ("aig esomeprprazole 40ml 28capsules", "AIG"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(parse_drug(raw).brand, expected)

    def test_components_match_rejects_unsafe_matches(self) -> None:
        cases = [
            ("VIGOTON PLUS 20 TABS", "VIGOTON 30 TABS", "different_modifier"),
            ("GYNOCONAZOLE 0.8%", "GYNOCONAZOL 0.4%", "different_dosage"),
            ("CLOZAPINE 100 MG 30 TABS", "CLOZAPEX 100 MG 50 TAB", "different_brand"),
            ("TOTAL COD LIVER OIL 120 ML SYP", "TOTAL SYRUP 120 ML", "different_brand"),
            ("FEROGLOBIN B12 30 CAP", "FEROGLOBIN 30 CAPS", "different_modifier"),
            ("CALCIUM D3 30 TAB", "CALCIUM 30 TAB", "different_modifier"),
            ("PANADOL EXTRA 24 TAB IMP", "PANADOL EXTRA 24 F.C. TAB", "different_import_status"),
            ("ASPOCID INF 30TAB", "ASPOCID 75 MG 30 TAB", "different_age_group"),
            ("CEFTRIAXONE 1 GM I.M. VIAL", "CEFTRIAXONE 1 GM I.V. VIAL", "different_route"),
            ("DIAMICRON 60 MR 30 TAB", "DIAMICRON MR 30 MG 30 TAB.", "different_dosage"),
            ("CENTRUM FOR MEN 30 TAB", "CENTRUM WOMEN 30 TAB", "different_modifier"),
            ("INSULINAGYPT R 100 UNITS 10 ML", "INSULINAGYPT 70 / 30 100 I.U. / ML ( 10 ML) VIAL", "different_modifier"),
            ("BETADINE 10% PRONTO 120 ML", "BETADINE VAGINAL DOUCHE 10 % 120 ML", "different_modifier"),
            ("GROWTH FORMULA ADULT CHOCOLATE", "GROWTH FORMULA FOR KIDS 400 GM POWDER CHOCOLATE", "different_age_group"),
            ("INSULINAGYPT 70/30 100 UNITS 10 ML", "INSULINAGYPT N 100 I.U. / ML (10 ML) VIAL", "different_modifier"),
            ("INSULINAGYPT 70/30 100 UNITS 10 ML", "INSULINAGYPT R 100 I.U. / ML (10 ML) VIAL", "different_modifier"),
            ("ESMATAC GELATIN CAPS", "ESMATAC D.R. CAPS", "different_modifier"),
            ("B-FRESH MOUTHWASH MINT", "B-FRESH GREEN MOUTH WASH 500 ML", "different_flavor"),
        ]
        for left, right, reason in cases:
            with self.subTest(left=left, right=right):
                is_ok, actual_reason = components_match(parse_drug(left), parse_drug(right))
                self.assertFalse(is_ok)
                self.assertEqual(actual_reason, reason)

    def test_components_match_accepts_equivalent_formatting(self) -> None:
        cases = [
            ("AUGMENTIN 625MG 10 TABS", "AUGMENTIN 625 MG 10 F.C. TAB."),
            ("INDERAL 10 MG 50TAB", "INDERAL 10 MG 50 TABS"),
            ("PANADOL NIGHT 20 TAB", "PANADOL NIGHT 20 TABLETS"),
            ("PANADOL EXTRA 24 TAB IMP", "PANADOL EXTRA 24 F.C. TAB IMP"),
            ("ALLERBAN SYRUP 120ML", "ALLERBAN 1 MG / 5 ML SYRUP 100 ML"),
            ("AMIKACIN 500MG VIAL", "AMIKACIN AMOUN 500 MG / 2 ML VIAL"),
            ("ASPOCID INF 30TAB", "ASPOCID PAEDIATRIC 75 MG 30 CHEWABLE TAB"),
            ("CEFTRIAXONE 1 GM I.M. VIAL", "CEFTRIAXONE 1 GM I.M / I.V VIAL"),
            ("AUGMENTIN DUO 200/28 MG/5 ML SUSP", "AUGMENTIN DUO 228 MG / 5 ML SUSP"),
            ("DOSTINEX .5 MG 2TAB", "DOSTINEX 0.5 MG 2 TAB"),
            ("BRETT VAG WASH 250ML", "BRETT VAGINAL WASH 250 ML"),
            ("ACYCLOVIR 400 MG 35 TAB", "ACYCLOVIR 400 STADA 35 TAB."),
            ("ADWIFLAM 50.ER. 20CAP", "ADWIFLAM 50 MG E.R. 20 CAPS."),
            ("ALBOTHYL 8 SUPP", "ALBOTHYL 90 MG 8 VAG. SUPP."),
            ("alphalipo 600 20tab", "ALPHALIPO 600 MG 20 F.C. TABS"),
            ("ALPHAVIM 300 - 20 CAPS", "ALPHAVIM 300 MG 20 CAPS"),
            ("AMRIZOLE N SUPP", "AMRIZOLE N 5 VAG. SUPP."),
            ("ANDOCANDOXIN 200 VAGINAL CAP", "ANDOCANDOXIN 200 MG 3 VAGINAL CAPS."),
            ("ANGIOFOX 20M", "ANGIOFOX (EFFOX) 20 MG 20 TABS."),
            ("ANORO ELLIPTA 62.5/25", "ANORO ELLIPTA 62.5 / 25 MCG INHALER 30 METERED DOSES"),
            ("ANTODINE 6 AMPOULES * 2 ML", "ANTODINE 20 MG / 2 ML 6 I.M. OR I.V. AMP"),
            ("APIDRA 5 CARTRIDGES", "APIDRA 100 I.U. / ML 5 CARTIRIDGES"),
            ("APIDRA SOLOSTAR 5 PENS", "APIDRA SOLOSTAR 100 I.U. / ML 5 PREFILLED PEN"),
            ("AUGMENTIN ES 600 MG 75ML SYP", "AUGMENTIN ES 600 PD. FOR ORAL SUSP. 75 ML"),
            ("AUGRAM 228.5 60ML SYRUP", "AUGRAM 228.5 MG / 5 ML PD. FOR ORAL SUSP. 60 ML"),
            ("azrolid 200 syrup 30 ml", "AZROLID 1200 / 30 ML SUSP"),
            ("AZROLID 200MG/5ML 15 ML SUSP", "AZROLID 600 / 15 ML SUSP"),
            ("AZROLID 200MG/5ML PD. FOR ORAL SUSP. 22.5ML", "AZROLID 900 / 22.5 ML SUSP"),
            ("CEFTRIAXONE 1 GM VIAL", "CEFTRIAXONE 1000 MG VIAL"),
            ("BECLOSONE FORTE 200 METERED", "BECLOSONE FORTE INHALER 0.1 MG / DOSE 200 DOSES"),
            ("BETMIGA 50 MG 30 TAB", "BETMIGA 50 MG 30 PROLONGED R.TABLETS"),
            ("BETOLVEX 2 pre-filled AMP", "BETOLVEX 1 MG / ML 2 PRE FILLED SYRINGE I.M."),
        ]
        for left, right in cases:
            with self.subTest(left=left, right=right):
                is_ok, reason = components_match(parse_drug(left), parse_drug(right))
                self.assertTrue(is_ok)
                self.assertEqual(reason, "ok")

    def test_components_match_rejects_conflicting_gm_mg_strengths(self) -> None:
        is_ok, reason = components_match(
            parse_drug("CEFTRIAXONE 2 GM VIAL"),
            parse_drug("CEFTRIAXONE 1000 MG VIAL"),
        )

        self.assertFalse(is_ok)
        self.assertEqual(reason, "different_dosage")

    def test_components_match_accepts_audited_false_negative_formats(self) -> None:
        cases = [
            ("ECTOMETHRIN 5%LOTION 50 ML", "ECTOMETHRIN 5 % LOTION 50 ML"),
            ("IVERZINE LOTION 6O ML", "IVERZINE 1 % LOTION 60 ML"),
            ("CONCOR 5 PLUS 30TAB", "CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS"),
            ("EPOETIN 4000 IU VIAL", "EPOETIN SEDICO 4000 I.U. / ML VIAL."),
            (
                "BEBELAC BEBEJUNIOR 3 MILK 400 GM",
                "BEBELAC 3 (BEBEJUNIOR 1 +) MILK 400 GM",
            ),
            ("PRISOLINE DROPS", "PRISOLINE EYE / NASAL DROPS 15 ML"),
            (
                "REXODIN 10% ANTISEPTIC SOLUTION 60 ML",
                "REXODIN ANTISEPTIC SOLUTION 60 ML",
            ),
            ("VITACID C EFF 12 TAB", "VITACID C 1 GM 12 EFF TAB"),
        ]
        for left, right in cases:
            with self.subTest(left=left, right=right):
                is_ok, reason = components_match(parse_drug(left), parse_drug(right))
                self.assertTrue(is_ok)
                self.assertEqual(reason, "ok")

    def test_parse_drug_translates_arabic_numerals_and_terms(self) -> None:
        comp = parse_drug("سوبراكس ١٠٠ مجم شراب ٣٠ مل")
        self.assertEqual(comp.dosage_nums, ("100",))
        self.assertEqual(comp.dosage_units, ("MG",))
        self.assertEqual(comp.volume, "30")
        self.assertEqual(comp.form, "SYRUP")

    def test_components_match_rejects_conflicting_critical_chemicals(self) -> None:
        # POTASSIUM vs CALCIUM
        is_ok, reason = components_match(
            parse_drug("POTASSIUM CHLORIDE 10%"),
            parse_drug("CALCIUM CHLORIDE 10%"),
        )
        self.assertFalse(is_ok)
        self.assertEqual(reason, "different_brand")

        # CETAL vs DOLIPRANE
        is_ok, reason = components_match(
            parse_drug("CETAL 250MG/5ML SUSP"),
            parse_drug("DOLIPRANE 250MG/5ML SUSP"),
        )
        self.assertFalse(is_ok)
        self.assertEqual(reason, "different_brand")

    def test_components_match_ignores_synthetic_dosage_mismatch(self) -> None:
        d = parse_drug("CHEMICETRIZINE 5 MG")
        m = parse_drug("CHEMICETRIZINE")  # no dosage
        m.is_synthetic = True
        is_ok, reason = components_match(d, m)
        self.assertTrue(is_ok)
        self.assertEqual(reason, "ok")


if __name__ == "__main__":
    unittest.main()
