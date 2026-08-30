"""H2 regression guard (post-fix): config flag semantics unchanged.

enable_auto_save_verified_match=False must still disable auto-save entirely.
"""

from __future__ import annotations

from tests.hypotheses.automatched._framework import (
    HypothesisCase, make_config,
)


class H2ConfigFlagOffTests(HypothesisCase):
    PROBABILITY = 30
    NAME = "H2 config flag off (regression guard)"

    def test_h2_default_flag_is_true(self) -> None:
        self.assertTrue(make_config().enable_auto_save_verified_match)

    def test_h2_flag_false_disables_auto_save(self) -> None:
        self.run_production_flow(config=make_config(enable_auto_save_verified_match=False))
        self.assertEqual(len(self.auto_rows()), 0)

    def test_h2_flag_true_saves_auto_matched(self) -> None:
        self.run_production_flow(config=make_config())
        self.assertEqual(len(self.auto_rows()), 1)
