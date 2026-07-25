"""Configuration constants for AI provider/model rotation.

Only ``PROVIDER_ORDER`` lives here now. The per-provider ``*_MODELS``
lists have moved to ``ai.providers.*`` in ``config.yaml`` and are
exposed via :class:`src.core.drug_matching.config.AIConfig.from_sources`.
"""

from __future__ import annotations

# Provider order for rotation.
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


__all__ = [
    "PROVIDER_ORDER",
]