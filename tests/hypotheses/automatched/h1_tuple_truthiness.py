"""H1 regression guard (post-fix): tuple truthiness bug stays fixed.

Pre-fix: _auto_save_verified_match did `if should_skip_auto_save_verified_match(...):`
where the helper returns tuple[bool, str] — always truthy, so every auto-save
returned early and nothing was persisted as auto_matched.

Post-fix contract (locked by these tests):
  1. The helper still returns a tuple (skip, reason).
  2. A healthy match produces skip=False -> row IS saved as auto_matched.
  3. The production flow persists the auto_matched row end-to-end.
"""

from __future__ import annotations

from tests.hypotheses.automatched._framework import (
    HypothesisCase, make_item, make_candidate,
)
from src.core.manual_review.manual_review_runtime import (
    should_skip_auto_save_verified_match,
)


class H1TupleTruthinessTests(HypothesisCase):
    PROBABILITY = 95
    NAME = "H1 tuple truthiness (regression guard)"

    def test_h1_helper_returns_tuple_not_bool(self) -> None:
        result = should_skip_auto_save_verified_match(
            make_item(), make_candidate(), None
        )
        self.assertIsInstance(result, tuple, "helper contract is a tuple")
        skip, reason = result
        self.assertFalse(skip)
        self.assertIsInstance(reason, str)

    def test_h1_healthy_candidate_is_not_skipped(self) -> None:
        """The exact regression: healthy match must not be 'skipped'."""
        skip, reason = should_skip_auto_save_verified_match(
            make_item(), make_candidate(), None
        )
        self.assertFalse(skip, f"healthy candidate skipped: {reason}")

    def test_h1_production_flow_saves_auto_matched(self) -> None:
        """End-to-end: perfect match-only run persists an auto_matched row."""
        self.run_production_flow()
        self.assertEqual(
            len(self.auto_rows()), 1,
            "REGRESSION: auto_matched row not saved; tuple-truthiness bug back?",
        )
