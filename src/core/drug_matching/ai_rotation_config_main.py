"""Main configuration constants for AI provider/model rotation."""

from __future__ import annotations

PROVIDER_ORDER = (
    "groq",
    "opencode",
    "openrouter",
    "github",
    "cerebras",
    "google",
    "mistral",
    "cloudflare",
)

__all__ = ["PROVIDER_ORDER"]
