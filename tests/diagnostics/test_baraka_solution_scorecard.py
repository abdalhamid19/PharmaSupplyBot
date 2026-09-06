"""Solution-selection contract for the Baraka Companies matching repair.

This public-API scorecard is intentionally red on the safety case before a
repair. A solution must reject an unrelated Arabic-only row, retain a verified
English match, and remain deterministic.
"""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import find_best_match_in_target
from src.core.utils.excel import Item


ITEM = Item(code="90951", name="INODEP CAPSULES 30", qty=1)
VERIFIED_ENGLISH = TargetProduct("inodp-ok", "INODEP CAPSULES 30", 1.0, 0.0)
UNRELATED_ARABIC = TargetProduct(
    "inodp-wrong",
    "\u0633\u0627\u0644\u0628\u0648\u0641\u0646\u062a 30 \u0642\u0631\u0635",
    1.0,
    0.0,
)


class TestBarakaSolutionScorecard(TestCase):
    """Acceptance criteria used to compare candidate fixes fairly."""

    def setUp(self) -> None:
        self.config = MatchingConfig(enable_bilingual_secondary_match=False)
        self.no_saved_review = patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision",
            return_value=None,
        )
        self.no_saved_review.start()
        self.addCleanup(self.no_saved_review.stop)

    def _match(self, catalog: list[TargetProduct]):
        return find_best_match_in_target(ITEM, "baraka-scorecard", catalog, self.config).decision

    def test_precision_gate_rejects_an_unrelated_arabic_row(self) -> None:
        """RED until the repair: no verified identity means no auto-match."""
        self.assertIsNone(self._match([UNRELATED_ARABIC]).best_match)

    def test_recall_gate_keeps_a_verified_exact_english_match(self) -> None:
        decision = self._match([VERIFIED_ENGLISH])
        self.assertIsNotNone(decision.best_match)
        self.assertEqual(decision.best_match.data["storeProductId"], "inodp-ok")

    def test_determinism_gate_is_stable_across_repeated_runs(self) -> None:
        first = self._match([VERIFIED_ENGLISH, UNRELATED_ARABIC])
        second = self._match([VERIFIED_ENGLISH, UNRELATED_ARABIC])
        self.assertEqual(
            first.best_match.data["storeProductId"],
            second.best_match.data["storeProductId"],
        )

