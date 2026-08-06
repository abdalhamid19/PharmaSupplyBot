"""Constants and dataclass for AI health test execution."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import get_provider_metadata

OPENCODE_BASE_URL = (
    get_provider_metadata("opencode").base_url
    if get_provider_metadata("opencode") is not None
    else "https://opencode.ai/zen/v1"
)

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
    """API key credentials for AI provider authentication."""

    name: str
    value: str


__all__ = ["OPENCODE_BASE_URL", "TEST_MESSAGES", "AIKey"]
