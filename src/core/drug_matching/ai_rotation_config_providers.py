"""Provider-specific model configurations for AI rotation."""

from __future__ import annotations

from .ai_rotation_config_groq import GROQ_MODELS
from .ai_rotation_config_opencode import OPENCODE_MODELS
from .ai_rotation_config_openrouter import OPENROUTER_MODELS
from .ai_rotation_config_cerebras import CEREBRAS_MODELS
from .ai_rotation_config_google import GOOGLE_MODELS
from .ai_rotation_config_mistral import MISTRAL_MODELS
from .ai_rotation_config_cloudflare import CLOUDFLARE_MODELS
from .ai_rotation_config_github import GITHUB_MODELS

DEFAULT_MODELS = {
    "groq": GROQ_MODELS,
    "opencode": OPENCODE_MODELS,
    "openrouter": OPENROUTER_MODELS,
    "cerebras": CEREBRAS_MODELS,
    "google": GOOGLE_MODELS,
    "mistral": MISTRAL_MODELS,
    "cloudflare": CLOUDFLARE_MODELS,
    "github": GITHUB_MODELS,
}

__all__ = [
    "GROQ_MODELS",
    "OPENCODE_MODELS",
    "OPENROUTER_MODELS",
    "CEREBRAS_MODELS",
    "GOOGLE_MODELS",
    "MISTRAL_MODELS",
    "CLOUDFLARE_MODELS",
    "GITHUB_MODELS",
    "DEFAULT_MODELS",
]
