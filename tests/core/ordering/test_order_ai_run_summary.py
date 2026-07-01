"""Tests for order AI trace summary grouping."""

from __future__ import annotations

import unittest

from src.core.ordering.order_ai_artifacts import summarize_order_ai_rows


class OrderAiRunSummaryTests(unittest.TestCase):
    """Validate compact AI/API artifact summaries."""

    def test_summarizes_statuses_and_provider_errors(self) -> None:
        rows = [
            {"phase": "ai_final", "ai_status": "ai_rejected"},
            {
                "phase": "api_attempt_verify",
                "provider": "groq",
                "status": "429",
                "error_code": "rate_limited",
                "decision": "disabled",
            },
            {
                "phase": "api_attempt_search",
                "provider": "opencode",
                "status": "200",
                "error_code": "invalid_json",
                "decision": "disabled",
            },
        ]

        summary = summarize_order_ai_rows(rows)

        self.assertIn(
            {"group": "ai_status", "value": "ai_rejected", "count": 1}, summary
        )
        self.assertIn(
            {"group": "provider_error", "value": "groq / 429 / rate_limited", "count": 1},
            summary,
        )


if __name__ == "__main__":
    unittest.main()
