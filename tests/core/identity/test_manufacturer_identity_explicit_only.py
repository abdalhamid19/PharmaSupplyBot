"""Manufacturer identity contract: explicit fields only, no name guessing.

Root problem measured on the live store (1232 distinct item names):
  - old heuristic ("last non-generic token is the manufacturer") claimed a
    manufacturer for 1230 names (99.8%), of which 1220 (99.0%) were invented
    product/dosage words, e.g.:
        'PANADOL EXTRA 24 TAB'        -> 'EXTRA'   (dosage descriptor)
        'ACTI-COLLA C 30SACHETS'      -> 'SACHETS' (packaging unit)
        'ACYCLOVIR 400 MG 35 TAB'     -> 'ACYCLOVIR' (active ingredient)
        'ULTRA PANADOL 10 TAB'        -> 'PANADOL' (brand, not company)
  - a curated-whitelist lookup claimed one for only 10 names (0.8%), all real.

New contract locked by these tests:
  1. Candidate side uses ONLY explicit companyName / supplierName. No name
     parsing fallback at all.
  2. Item (query) side never guesses; it recognises curated manufacturer
     tokens only (KNOWN_MANUFACTURERS), otherwise returns None.
  3. A missing manufacturer on either side means "no conflict" (unchanged).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.identity.manufacturer_identity import (  # noqa: E402
    extract_manufacturer_from_candidate,
    extract_manufacturer_from_name,
    manufacturer_conflict,
)


class NoGuessingFromItemNameTests(unittest.TestCase):
    """Item names must not yield invented manufacturers."""

    def test_dosage_descriptor_is_not_a_manufacturer(self) -> None:
        self.assertIsNone(extract_manufacturer_from_name("PANADOL EXTRA 24 TAB"))

    def test_packaging_unit_is_not_a_manufacturer(self) -> None:
        self.assertIsNone(extract_manufacturer_from_name("ACTI-COLLA C 30SACHETS"))

    def test_active_ingredient_is_not_a_manufacturer(self) -> None:
        self.assertIsNone(extract_manufacturer_from_name("ACYCLOVIR 400 MG 35 TAB"))

    def test_brand_name_is_not_a_manufacturer(self) -> None:
        self.assertIsNone(extract_manufacturer_from_name("ULTRA PANADOL 10 TAB"))

    def test_product_word_is_not_a_manufacturer(self) -> None:
        self.assertIsNone(
            extract_manufacturer_from_name("CO AVAZIR 5GM EYE OINTMENT")
        )

    def test_empty_name_returns_none(self) -> None:
        self.assertIsNone(extract_manufacturer_from_name(""))


class KnownManufacturerRecognitionTests(unittest.TestCase):
    """Curated manufacturer tokens are still recognised (recognition, not guessing)."""

    def test_known_manufacturer_suffix_is_recognised(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_name("METHYL FOLATE 30 CAP ORCHIDIA"),
            "ORCHIDIA",
        )

    def test_known_manufacturer_mid_name_is_recognised(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_name("METHYL FOLATE ORA 30 CAPS"), "ORA"
        )

    def test_known_manufacturer_in_parentheses_is_recognised(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_name("METHYL FOLATE (ORCHIDIA) 30 CAPS"),
            "ORCHIDIA",
        )

    def test_last_known_manufacturer_wins(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_name("EVA SOMETHING 10 TAB ORCHIDIA"),
            "ORCHIDIA",
        )


class CandidateExplicitFieldsOnlyTests(unittest.TestCase):
    """Candidate manufacturer comes only from explicit API fields."""

    def test_company_name_is_used(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_candidate("PANADOL EXTRA 24 TAB", "GSK"),
            "GSK",
        )

    def test_supplier_name_is_fallback_for_company(self) -> None:
        self.assertEqual(
            extract_manufacturer_from_candidate(
                "PANADOL EXTRA 24 TAB", None, "HIKMA PHARMA"
            ),
            "HIKMA",
        )

    def test_no_explicit_field_yields_none_not_a_name_guess(self) -> None:
        """The old code fell back to guessing from the candidate name."""
        self.assertIsNone(
            extract_manufacturer_from_candidate("PANADOL EXTRA 24 TAB", None, None)
        )

    def test_blank_explicit_fields_yield_none(self) -> None:
        self.assertIsNone(
            extract_manufacturer_from_candidate("PANADOL EXTRA 24 TAB", "", "   ")
        )


class ConflictBehaviourTests(unittest.TestCase):
    """End-to-end conflict outcomes for the pairs that mattered."""

    def test_no_false_conflict_for_dosage_word_vs_real_company(self) -> None:
        """The regression that blocked auto-save: 'EXTRA' vs 'GSK'."""
        item_mfg = extract_manufacturer_from_name("PANADOL EXTRA 24 TAB")
        cand_mfg = extract_manufacturer_from_candidate(
            "PANADOL EXTRA 24 TAB", "GSK"
        )
        self.assertIsNone(item_mfg)
        self.assertEqual(cand_mfg, "GSK")
        self.assertFalse(manufacturer_conflict(item_mfg, cand_mfg))

    def test_real_conflict_still_detected(self) -> None:
        """ORCHIDIA vs ORA stays a conflict (documented real mismatch)."""
        item_mfg = extract_manufacturer_from_name("METHYL FOLATE 30 CAP ORCHIDIA")
        cand_mfg = extract_manufacturer_from_candidate(
            "METHYL FOLATE ORA 30 CAPS", "ORA"
        )
        self.assertEqual(item_mfg, "ORCHIDIA")
        self.assertEqual(cand_mfg, "ORA")
        self.assertTrue(manufacturer_conflict(item_mfg, cand_mfg))

    def test_same_company_is_not_a_conflict(self) -> None:
        item_mfg = extract_manufacturer_from_name("PANADOL TAB GSK")
        cand_mfg = extract_manufacturer_from_candidate("PANADOL TAB", "GSK")
        self.assertFalse(manufacturer_conflict(item_mfg, cand_mfg))


if __name__ == "__main__":
    unittest.main()
