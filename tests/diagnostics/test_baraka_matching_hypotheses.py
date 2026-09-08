"""Executable investigation of false positive matching in Baraka Companies.

These tests intentionally contain two red regression assertions.  They encode
the operator's safety contract: an Arabic-only Excel row without proven brand
identity must never be auto-accepted merely because a strength, pack size, or
form token is shared.  Do not weaken or xfail these assertions; they are the
pass/fail gate for a future fix.
"""

from __future__ import annotations

from unittest import TestCase

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import find_best_match_in_target
from src.core.matching.matching_rules import acceptance_details
from src.core.matching.product_matching_acceptance import _candidate_variant_rejection
from src.core.matching.product_matching_scoring import (
    _best_candidate_overlap,
    _candidate_english_name,
    _normalize_text,
    _numeric_match_count,
)
from src.core.utils.excel import Item


INODEP = Item(code="90951", name="INODEP CAPSULES 30", qty=1)
UNRELATED_ARABIC_TABLETS = TargetProduct(
    code="unrelated-30",
    name="\u0633\u0627\u0644\u0628\u0648\u0641\u0646\u062a 30 \u0642\u0631\u0635",
    price=1.0,
    discount_percent=0.0,
)


def _acceptance_helpers() -> tuple:
    """Return the helper tuple required by the legacy threshold contract."""
    return (
        _normalize_text,
        _candidate_english_name,
        _best_candidate_overlap,
        _numeric_match_count,
    )


class TestBarakaMatchingHypotheses(TestCase):
    """One executable probe for every ranked causal hypothesis."""

    def setUp(self) -> None:
        self.config = MatchingConfig(enable_bilingual_secondary_match=False)
        self.candidate = UNRELATED_ARABIC_TABLETS.to_candidate_dict()

    def test_h1_threshold_contract_rejects_the_unrelated_candidate(self) -> None:
        """Control: configured threshold rules correctly reject this row."""
        accepted, _reason, rejection = acceptance_details(
            INODEP.name,
            self.candidate,
            score=12.33,
            matching_config=self.config,
            helpers=_acceptance_helpers(),
        )
        self.assertFalse(accepted)
        self.assertIn("Rejected: overlap=", rejection)

    def test_h1_production_matcher_must_honor_the_threshold_contract(self) -> None:
        """RED now: current production acceptance bypasses the threshold gate."""
        decision = find_best_match_in_target(
            INODEP, "baraka-diagnostic", [UNRELATED_ARABIC_TABLETS], self.config
        ).decision
        self.assertIsNone(
            decision.best_match,
            "An unrelated Arabic-only 30-tablet row must be no-results/manual review, "
            "not an automatic INODEP match.",
        )

    def test_h2_excel_target_requires_brand_identity_evidence(self) -> None:
        """RED now: excelTarget currently suppresses the identity-token guard."""
        rejection = _candidate_variant_rejection(INODEP.name, self.candidate)
        self.assertTrue(
            rejection,
            "A candidate with no INODEP brand evidence must be rejected before "
            "score/strength/form can qualify it.",
        )

    def test_h3_catalog_schema_is_single_name_and_not_an_english_identity_source(self) -> None:
        """Arabic supplier text is retained raw but never presented as English."""
        self.assertEqual(self.candidate["productName"], UNRELATED_ARABIC_TABLETS.name)
        self.assertEqual(self.candidate["productNameEn"], "")
        self.assertFalse(self.candidate["verified_brand_identity"])

    def test_h4_bilingual_fallback_is_not_needed_to_reproduce_false_acceptance(self) -> None:
        """Confirmed: fallback is not responsible for the false acceptance."""
        decision = find_best_match_in_target(
            INODEP, "baraka-diagnostic", [UNRELATED_ARABIC_TABLETS], self.config
        ).decision
        self.assertNotIn("bilingual fallback", (decision.final_reason or "").lower())

    def test_h5_false_candidate_has_only_generic_shared_evidence(self) -> None:
        """Confirmed: the sole shared input signal is generic pack/form evidence."""
        self.assertLess(_best_candidate_overlap(INODEP.name, self.candidate), 0.6)
        self.assertIn("30", _normalize_text(INODEP.name))
        self.assertIn("30", _normalize_text(self.candidate["productName"]))
