import unittest

from src.core.product_matching import (
    _search_queries_for_item,
    explain_best_product_match,
)
from src.core.utils.excel import Item


class ProductMatchingQueryTests(unittest.TestCase):
    def test_search_queries_include_normalized_dosage_variants(self) -> None:
        item = Item(code="92037", name="QUINSTIBOWL 5MG 20F.C TABS", qty=3)

        queries = _search_queries_for_item(item)

        self.assertIn("QUINSTIBOWL 5MG 20F.C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20 F C TABS", queries)
        self.assertIn("QUINSTIBOWL 5 MG 20", queries)
        self.assertIn("92037", queries)
        self.assertIn("5 MG", queries)
        self.assertIn("F", queries)
        self.assertLessEqual(len(queries), 24)

    def test_short_names_include_code_fallback_after_unique_variants(self) -> None:
        item = Item(code="73368", name="KENACOMB CREAM", qty=1)

        queries = _search_queries_for_item(item)

        self.assertGreaterEqual(len(queries), 4)
        self.assertIn("73368", queries)
        self.assertIn("CREAM", queries)

    def test_search_queries_fix_common_zero_ocr_in_pack_size(self) -> None:
        item = Item(code="47273", name="IVERZINE LOTION 6O ML", qty=1)

        queries = _search_queries_for_item(item)

        self.assertIn("IVERZINE LOTION 60 ML", queries)

    def test_arabic_variant_guard_rejects_wrong_bebelac_ar_row(self) -> None:
        item = Item(code="80131", name="BEBELAC AR MILK", qty=1)
        decision = explain_best_product_match(item, [(item.name, _bebelac_results())])

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productName"], "بيبيلاك ايه ار لبن 400 جم"
        )

    def test_arabic_variant_guard_rejects_wrong_iverzine_form(self) -> None:
        item = Item(code="47273", name="IVERZINE LOTION 6O ML", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        {
                            "productNameEn": "IVERZINE LOTION O ML 6 24",
                            "productName": "ايفرزين 6 مجم 24 اقراص",
                            "availableQuantity": 5,
                            "productsCount": 5,
                        }
                    ],
                )
            ],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("LOTION", decision.final_reason)

    def test_arabic_variant_guard_rejects_vitacid_calcium(self) -> None:
        item = Item(code="73368", name="VITACID C EFF 12 TAB", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _candidate(
                            "VITACID C EFF TAB 12", "فيتاسيد كالسيوم 12 اقراص فوار"
                        )
                    ],
                )
            ],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("calcium", decision.final_reason)

    def test_synthetic_dom_match_rejects_generic_syrup_query(self) -> None:
        item = Item(code="73387", name="IVYPRONT COUGH 100 ML SYRUP", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _synthetic_candidate(
                            "ML SYRUP 1 100", "ابيكسيدون 1 مجم / مل شراب 100 مل"
                        )
                    ],
                )
            ],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("identity token", decision.final_reason)

    def test_vaginal_douche_requires_arabic_variant_marker(self) -> None:
        item = Item(code="73328", name="BETADINE VAG DOUCHE 120 ML", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _synthetic_candidate(
                            "BETADINE VAG DOUCHE 120", "بيتادين محلول مطهر 120 مل"
                        )
                    ],
                )
            ],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("VAG", decision.final_reason)

    def test_apple_flavor_requires_arabic_flavor_marker(self) -> None:
        item = Item(code="80111", name="Pedialyte Apple Flavour oral solution", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _synthetic_candidate(
                            "PEDIALYTE ORAL SOLUTION 200", "بيديالايت محلول جفاف 200 مل"
                        )
                    ],
                )
            ],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("APPLE", decision.final_reason)

    def test_semantic_conflict_rejects_isis_detox_for_anise(self) -> None:
        item = Item(code="87778", name="ISIS ANISE 20BAGS", qty=1)
        decision = explain_best_product_match(
            item,
            [(item.name, [_candidate("ISIS DETOX 20 BAGS", "ايزيس ديتوكس 20 فتلة")])],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn("Semantic token conflict", decision.final_reason)

    def test_unrequested_advanced_variant_loses_to_plain_polyfresh(self) -> None:
        item = Item(code="12345", name="POLYFRESH EYE DROPS 10 ML", qty=1)
        decision = explain_best_product_match(
            item,
            [
                (
                    item.name,
                    [
                        _candidate(
                            "POLYFRESH ADVANCED EYE DROPS 10 ML", "بولى فريش 10 مل"
                        ),
                        _candidate("POLYFRESH 2% EYE DROPS 10 ML", "بولى فريش 10 مل"),
                    ],
                )
            ],
        )

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(
            decision.best_match.data["productNameEn"], "POLYFRESH 2% EYE DROPS 10 ML"
        )

    def test_short_fallback_query_still_requires_original_identity(self) -> None:
        item = Item(code="89590", name="***IMP***ENDOXAN 1 GM I.V. VIAL", qty=1)
        decision = explain_best_product_match(
            item,
            [("1 GM", [_candidate("PARACETAMOL 1 GM / 100 ML VIAL", "باراسيتامول")])],
        )

        self.assertIsNone(decision.best_match)
        self.assertIn(
            "English name missing requested identity token", decision.final_reason
        )

    def test_missing_store_product_id_is_not_orderable(self) -> None:
        item = Item(code="73241", name="MINALAX 10 TAB", qty=1)
        candidate = _candidate("MINALAX 10 TAB.", "مينالاكس 10 اقراص")
        candidate.pop("storeProductId")

        decision = explain_best_product_match(item, [(item.name, [candidate])])

        self.assertIsNone(decision.best_match)
        self.assertIn("storeProductId", decision.final_reason)

    def test_duplicate_candidate_across_queries_is_scored_once(self) -> None:
        item = Item(code="123", name="PANADOL 24 TAB", qty=1)
        candidate = _candidate("PANADOL 24 TAB", "بنادول 24 قرص")
        decision = explain_best_product_match(
            item,
            [("PANADOL 24 TAB", [candidate]), ("PANADOL", [dict(candidate)])],
        )

        self.assertEqual(len(decision.diagnostics), 1)

    def test_tie_break_prefers_available_discounted_lower_price_candidate(self) -> None:
        item = Item(code="21058", name="MIDODRINE 2.5 mg 20 TAB", qty=1)
        low_stock = _candidate("MIDODRINE 2.5 MG 20 TAB.", "ميدودرين")
        low_stock.update({"storeProductId": "low", "availableQuantity": 2})
        high_stock = _candidate("MIDODRINE 2.5 MG 20 TAB.", "ميدودرين")
        high_stock.update(
            {
                "storeProductId": "high",
                "availableQuantity": 8,
                "discountPercent": 10.0,
                "salePrice": 20.0,
            }
        )

        decision = explain_best_product_match(item, [(item.name, [low_stock, high_stock])])

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["storeProductId"], "high")

    def test_equal_accepted_candidates_with_different_ids_require_review(self) -> None:
        item = Item(code="78379", name="NESTOGEN 3 MILK 200GM", qty=1)
        first = _candidate("NESTOGEN 3 MILK 200 GM", "نستوجين")
        first["storeProductId"] = "2630924"
        second = _candidate("NESTOGEN 3 MILK 200 GM", "نستوجين")
        second["storeProductId"] = "2695428"

        decision = explain_best_product_match(item, [(item.name, [first, second])])

        self.assertIsNone(decision.best_match)
        self.assertIn("Ambiguous accepted candidates", decision.final_reason)

    def test_fuzzy_match_with_extra_numeric_tokens_requires_review(self) -> None:
        item = Item(code="74881", name="OCTOZINC CAP", qty=1)
        candidate = _candidate("OCTOZINC 25 MG 20 CAPS.", "اوكتوزنك")

        decision = explain_best_product_match(item, [(item.name, [candidate])])

        self.assertIsNone(decision.best_match)
        self.assertIn("unrequested numeric token", decision.final_reason)

    def test_attached_unit_numbers_match_spaced_candidate_numbers(self) -> None:
        item = Item(code="61862", name="AMLODIPINE 5MG 30 TAB", qty=1)
        candidate = _candidate("AMLODIPINE 5 MG 30 TAB.", "املوديبين")

        decision = explain_best_product_match(item, [(item.name, [candidate])])

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], candidate["productNameEn"])

    def test_liquid_per_5_ml_marker_does_not_block_fuzzy_match(self) -> None:
        item = Item(code="32158", name="SUPRAX 100MG SYRUP 30ML", qty=1)
        candidate = _candidate("SUPRAX 100 MG / 5 ML SUSP. 30 ML", "سوبراكس 30 مل")

        decision = explain_best_product_match(item, [(item.name, [candidate])])

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], candidate["productNameEn"])

    def test_unit_dose_pack_markers_do_not_block_vial_match(self) -> None:
        item = Item(code="AT50", name="ATROVENT 500 MCG VIAL", qty=1)
        candidate = _candidate(
            "ATROVENT 500 MCG / 2 ML 20 UNIT DOSE VIAL.", "اتروفنت"
        )

        decision = explain_best_product_match(item, [(item.name, [candidate])])

        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["productNameEn"], candidate["productNameEn"])

    def test_safe_omitted_topical_strength_does_not_block_match(self) -> None:
        cases = [
            ("26979", "IVERZINE LOTION 6O ML", "IVERZINE 1 % LOTION 60 ML"),
            ("83061", "CLOSOL 50 ML SPRAY", "CLOSOL 10 MG / ML TOPICAL SPRAY 50 ML"),
            (
                "89588",
                "REXODIN 10% ANTISEPTIC SOLUTION 60 ML",
                "REXODIN ANTISEPTIC SOLUTION 60 ML",
            ),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                candidate = _candidate(candidate_name, "")
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [candidate])],
                )
                self.assertIsNotNone(decision.best_match)

    def test_safe_omitted_combo_and_effervescent_strengths_match(self) -> None:
        cases = [
            (
                "73173",
                "CONCOR 5 PLUS 30TAB",
                "CONCOR PLUS 5 / 12.5 MG 30 F.C. TABLETS",
            ),
            ("73267", "VITACID C EFF 12 TAB", "VITACID C 1 GM 12 EFF TAB"),
        ]
        for code, item_name, candidate_name in cases:
            with self.subTest(item_name=item_name):
                candidate = _candidate(candidate_name, "")
                decision = explain_best_product_match(
                    Item(code=code, name=item_name, qty=1),
                    [(item_name, [candidate])],
                )
                self.assertIsNotNone(decision.best_match)


def _bebelac_results() -> list[dict[str, object]]:
    """Return Bebelac candidates with one false high-scoring row and one real row."""
    return [
        _candidate("BEBELAC AR MILK", "لبن بيبلاك بريماتيور", 1),
        _candidate("BEBELAC AR MILK 400", "بيبيلاك ايه ار لبن 400 جم", 0),
    ]


def _candidate(english_name: str, arabic_name: str, qty: int = 3) -> dict[str, object]:
    """Return a Tawreed-style product candidate."""
    return {
        "productNameEn": english_name,
        "productName": arabic_name,
        "availableQuantity": qty,
        "productsCount": qty,
        "storeProductId": f"store-{english_name}",
    }


def _synthetic_candidate(english_name: str, arabic_name: str) -> dict[str, object]:
    """Return a DOM fallback product candidate with no real English name."""
    candidate = _candidate("", arabic_name)
    candidate["productNameEnFallback"] = english_name
    candidate["productNameEnSynthetic"] = True
    return candidate


if __name__ == "__main__":
    unittest.main()
