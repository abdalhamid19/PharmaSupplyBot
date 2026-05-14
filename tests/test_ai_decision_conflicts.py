"""Tests for AI decision conflict resolution."""

from __future__ import annotations

import unittest

from src.core.drug_matching.verifier import _resolve_ai_conflicts


class AiDecisionConflictTests(unittest.TestCase):
    """Validate _resolve_ai_conflicts detects and resolves contradictions."""

    def test_hard_conflict_critical_overrides_is_correct(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.92,
            "reason": "same brand",
            "hard_conflicts": ["different_strength"],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        self.assertIn("hard_conflict_override", resolved["reason"])
        self.assertLessEqual(resolved["confidence"], 0.55)

    def test_hard_conflict_dosage_forces_reject(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.88,
            "reason": "matching product",
            "hard_conflicts": ["different_dosage"],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        self.assertIn("different_dosage", resolved["reason"])

    def test_hard_conflict_noncritical_caps_confidence(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.95,
            "reason": "same brand and dosage",
            "hard_conflicts": ["different_form"],
        }
        resolved = _resolve_ai_conflicts(result)
        # Non-critical conflicts don't override is_correct but cap confidence
        self.assertTrue(resolved["is_correct"])
        self.assertLessEqual(resolved["confidence"], 0.72)

    def test_decision_reject_overrides_is_correct_true(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.8,
            "reason": "some reason",
            "decision": "reject",
            "hard_conflicts": [],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        self.assertIn("decision_reject_override", resolved["reason"])
        self.assertLessEqual(resolved["confidence"], 0.6)

    def test_no_conflict_passes_through(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.92,
            "reason": "correct match",
            "decision": "accept",
            "hard_conflicts": [],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertTrue(resolved["is_correct"])
        self.assertEqual(resolved["confidence"], 0.92)
        self.assertEqual(resolved["reason"], "correct match")

    def test_already_rejected_not_modified(self) -> None:
        result = {
            "is_correct": False,
            "confidence": 0.85,
            "reason": "mismatch",
            "decision": "reject",
            "hard_conflicts": ["different_strength"],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        # Reason not modified because is_correct was already False
        self.assertEqual(resolved["reason"], "mismatch")

    def test_hard_conflicts_string_format_parsed(self) -> None:
        """AI sometimes returns hard_conflicts as comma-separated string."""
        result = {
            "is_correct": True,
            "confidence": 0.9,
            "reason": "ok",
            "hard_conflicts": "different_concentration, different_route",
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        self.assertIn("hard_conflict_override", resolved["reason"])

    def test_mixed_critical_and_noncritical_uses_critical(self) -> None:
        result = {
            "is_correct": True,
            "confidence": 0.91,
            "reason": "ok",
            "hard_conflicts": ["different_form", "different_active_ingredient"],
        }
        resolved = _resolve_ai_conflicts(result)
        self.assertFalse(resolved["is_correct"])
        self.assertIn("different_active_ingredient", resolved["reason"])


if __name__ == "__main__":
    unittest.main()
