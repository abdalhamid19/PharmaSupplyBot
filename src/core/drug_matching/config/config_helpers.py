"""Helper functions for configuration loading and resolution."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .config_models import AIConfig, Paths
from .config_providers import PROVIDERS

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Adjust the matching logger level only — no handler setup.

    .. deprecated::
        The matching workflow now flows through the unified logging
        configured by :func:`src.cli.logging_setup.configure_logging`.
        Calling this used to invoke ``logging.basicConfig`` which
        destroyed the file handlers installed by the unified setup,
        causing ``logs/app.log`` to silently lose matching records.

        This function is preserved so existing callers do not break,
        but it now ONLY adjusts the matching package's root logger
        level — no handlers are installed, no ``basicConfig`` is
        called.
    """
    # Adjust the matching package root so every submodule
    # (which uses getLogger(__name__)) inherits the new level.
    matching_root = logging.getLogger("src.core.drug_matching")
    matching_root.setLevel(getattr(logging, level.upper(), logging.INFO))


def load_env(path: Path | None = None) -> None:
    """Load simple KEY=VALUE lines from the project .env file."""
    env_path = path or Paths().env_file
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        _load_env_line(line)


def resolve_api_config(provider: str = "", model: str = "", api_key: str = "") -> dict:
    """Resolve API settings from arguments and environment variables.

    The ``model`` and ``api_key`` arguments take precedence over the
    environment. When neither is set, the resolution falls back to
    :class:`AIConfig`, which itself reads ``ai:`` from ``config.yaml``
    (then env, then hardcoded defaults).
    """
    if provider and provider in PROVIDERS:
        return _provider_api_config(provider, model, api_key)
    keys = _configured_env_key_values()
    ai_defaults = AIConfig.from_sources()
    return {
        "api_key": api_key or os.getenv("OPENROUTER_API_KEY", ""),
        "api_keys": _dedupe((api_key, *keys)),
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "model": model or os.getenv("AI_MODEL", "").strip() or ai_defaults.primary_model,
        "fallback_models": _fallback_models(),
    }


def _provider_api_config(provider: str, model: str, api_key: str) -> dict:
    info = PROVIDERS[provider]
    keys = _dedupe((api_key, *(os.getenv(key, "") for key in info["env_keys"])))
    from .config_providers import provider_base_url
    ai_defaults = AIConfig.from_sources()
    ai_pool = ai_defaults.provider(provider)
    default_model = (
        ai_pool.default_model if ai_pool is not None else info.get("default_model", "")
    )
    return {
        "api_key": keys[0] if keys else "",
        "api_keys": keys,
        "base_url": provider_base_url(info),
        "model": model
        or os.getenv("AI_MODEL", "").strip()
        or default_model,
        "fallback_models": _fallback_models(),
    }


def _load_env_line(line: str) -> None:
    text = line.strip()
    if not text or text.startswith("#") or "=" not in text:
        return
    key, value = text.split("=", 1)
    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _configured_env_key_values() -> tuple[str, ...]:
    keys = [key for info in PROVIDERS.values() for key in info.get("env_keys", ())]
    return tuple(os.getenv(key, "") for key in keys if os.getenv(key, ""))


def _fallback_models() -> tuple[str, ...]:
    """Resolve the ``FALLBACK_MODELS`` list using the standard precedence.

    Order: ``FALLBACK_MODELS`` env var → ``ai.fallback_models`` in
    ``config.yaml`` → :class:`AIConfig` dataclass defaults.
    """
    env_value = os.getenv("FALLBACK_MODELS", "")
    env_models = tuple(
        model.strip() for model in env_value.split(",") if model.strip()
    )
    if env_models:
        return env_models
    return AIConfig.from_sources().fallback_models


def _dedupe(values) -> tuple[str, ...]:
    seen = set()
    return tuple(
        value for value in values if value and value not in seen and not seen.add(value)
    )


__all__ = [
    "setup_logging",
    "load_env",
    "resolve_api_config",
    "_provider_api_config",
    "_load_env_line",
    "_configured_env_key_values",
    "_fallback_models",
    "_dedupe",
]
