"""Constants and dataclass for AI health test execution."""

from __future__ import annotations

from dataclasses import dataclass

from .config import PROVIDERS

OPENCODE_BASE_URL = PROVIDERS["opencode"]["base_url"]

TEST_MESSAGES = [
    {
        "role": "system",
        "content": (
            "Return JSON only. You verify whether two drug product names are "
            "the same sellable product."
        ),
    },
    {
        "role": "user",
        "content": (
            'Are these the same product? A="PANADOL 20 TAB", '
            'B="PANADOL 20 TABLETS". Return exactly: '
            '{"is_correct": true, "reason": "brief", "confidence": 0.0-1.0}'
        ),
    },
]


@dataclass(frozen=True, slots=True)
class AIKey:
    name: str
    value: str


__all__ = ["OPENCODE_BASE_URL", "TEST_MESSAGES", "AIKey"]
