"""Tests for Tawreed DOM product field normalization."""

from __future__ import annotations

import unittest

from src.tawreed.tawreed_dom_fallback import fallback_english_name


class TawreedDomFieldsTests(unittest.TestCase):
    """Validate synthetic English names built from DOM-only product rows."""

    def test_fallback_keeps_query_order_when_dom_numbers_match(self) -> None:
        self.assertEqual(
            fallback_english_name(
                "CHEMICETRIZINE 5 MG20 TAB",
                "CHEMICETRIZINE MG TAB 5 20",
            ),
            "CHEMICETRIZINE 5 MG 20 TAB",
        )
        self.assertEqual(
            fallback_english_name("DIVIDO 75 MG 30 TAB", "DIVIDO MG TAB 75 30"),
            "DIVIDO 75 MG 30 TAB",
        )

    def test_fallback_still_adds_dom_pack_numbers_missing_from_query(self) -> None:
        self.assertEqual(
            fallback_english_name("BEBELAC AR MILK", "بيبيلاك ايه ار لبن 400 جم"),
            "BEBELAC AR MILK 400",
        )


if __name__ == "__main__":
    unittest.main()
