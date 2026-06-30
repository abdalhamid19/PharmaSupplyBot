"""Tests for per-run AI provider cooldown."""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from src.core.drug_matching.ai.ai_provider_cooldown import apply_provider_cooldown


@dataclass(frozen=True)
class Attempt:
    provider: str
    api_key: str
    model: str


class ProviderCooldownTests(unittest.TestCase):
    """Validate provider-level cooldown without real network calls."""

    def test_repeated_rate_limits_disable_provider_attempts(self) -> None:
        verifier = self._verifier()
        first = self._result("groq", "rate_limited")
        second = self._result("groq", "rate_limited")

        self.assertEqual(apply_provider_cooldown(verifier, first), set())
        disabled = apply_provider_cooldown(verifier, second)

        self.assertEqual(disabled, {"groq"})
        self.assertIn(("groq", "abc123", "m1"), verifier._failed_combos)
        self.assertIn(("groq", "abc123", "m2"), verifier._failed_combos)
        self.assertNotIn(("openrouter", "xyz789", "m3"), verifier._failed_combos)
        self.assertEqual(second["_provider_cooldown"], "groq")

    def test_invalid_json_counts_for_cooldown(self) -> None:
        verifier = self._verifier()

        apply_provider_cooldown(verifier, self._result("opencode", "invalid_json"))
        disabled = apply_provider_cooldown(
            verifier, self._result("opencode", "invalid_json")
        )

        self.assertEqual(disabled, {"opencode"})
        self.assertIn(("opencode", "opn456", "m4"), verifier._failed_combos)

    def test_retry_after_rate_limit_disables_provider_immediately(self) -> None:
        verifier = self._verifier()

        disabled = apply_provider_cooldown(
            verifier,
            self._result("groq", "rate_limited", reason="429 retry_after=120"),
        )

        self.assertEqual(disabled, {"groq"})
        self.assertIn(("groq", "abc123", "m1"), verifier._failed_combos)

    @staticmethod
    def _verifier():
        return SimpleNamespace(
            _failed_combos=set(),
            _cfg=SimpleNamespace(
                attempt_plan=(
                    Attempt("groq", "key-abc123", "m1"),
                    Attempt("groq", "key-abc123", "m2"),
                    Attempt("openrouter", "key-xyz789", "m3"),
                ),
                review_attempt_plan=(Attempt("opencode", "key-opn456", "m4"),),
            ),
        )

    @staticmethod
    def _result(provider: str, error_code: str, reason: str = "") -> dict:
        return {
            "_api_attempts": [
                {
                    "provider": provider,
                    "key_suffix": "abc123",
                    "model": "m1",
                    "error_code": error_code,
                    "reason": reason,
                }
            ]
        }


if __name__ == "__main__":
    unittest.main()
