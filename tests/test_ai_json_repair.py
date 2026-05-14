"""Tests for AI JSON response repair."""

from __future__ import annotations

import unittest

from src.core.drug_matching.verifier import _extract_json


class AiJsonRepairTests(unittest.TestCase):
    """Validate safe parsing of common model JSON formatting noise."""

    def test_extract_json_repairs_fenced_trailing_comma(self) -> None:
        parsed = _extract_json(
            '```json\n{"is_correct": true, "reason": "ok", "confidence": 0.91,}\n```'
        )

        self.assertIsNotNone(parsed)
        self.assertTrue(parsed["is_correct"])
        self.assertEqual(parsed["reason"], "ok")

    def test_extract_json_keeps_unparseable_text_rejected(self) -> None:
        self.assertIsNone(_extract_json("same product but no JSON object"))

    def test_extract_json_recovers_partial_search_decision_safely(self) -> None:
        parsed = _extract_json(
            '{"decision":"accept","best_index":1,'
            '"reason":"brand and form match but response truncated'
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["decision"], "accept")
        self.assertEqual(parsed["best_index"], 1)
        self.assertEqual(parsed["confidence"], 0.5)


if __name__ == "__main__":
    unittest.main()
