"""Helper functions for configuration loading and resolution."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .config_models import AIConfig, Paths, get_provider_metadata
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
    """Resolve API settings from arguments and ``config.yaml``.

    The ``model`` and ``api_key`` arguments take precedence over the
    YAML. When neither is set, the resolution falls back to
    :class:`AIConfig`, which reads ``ai:`` from ``config.yaml``.

    **No environment-variable overrides** — only explicit args and
    YAML config participate in the resolution.
    """
    if provider and provider in PROVIDERS:
        return _provider_api_config(provider, model, api_key)
    keys = _configured_env_key_values()
    ai_defaults = AIConfig.from_sources()
    return {
        "api_key": api_key or keys[0] if keys else "",
        "api_keys": _dedupe((api_key, *keys)),
        "base_url": _resolve_base_url(""),
        "model": model or ai_defaults.primary_model,
        "fallback_models": ai_defaults.fallback_models,
    }


def _resolve_base_url(fallback: str) -> str:
    """Resolve the API base URL from the YAML config.

    Falls back to ``fallback`` (which itself defaults to
    ``https://openrouter.ai/api/v1``) when the YAML has no value.
    """
    return fallback or "https://openrouter.ai/api/v1"


def _provider_api_config(provider: str, model: str, api_key: str) -> dict:
    info = PROVIDERS.get(provider, {})
    meta = get_provider_metadata(provider)
    # Use the YAML-derived metadata when present, otherwise the legacy
    # PROVIDERS dict (preserves behaviour for un-migrated configs).
    env_keys = meta.env_keys if meta is not None else info.get("env_keys", ())
    base_url = meta.base_url if meta is not None else str(info.get("base_url", ""))
    keys = _dedupe((api_key, *(_configured_keys_for(env_keys))))
    from .config_providers import provider_base_url
    ai_defaults = AIConfig.from_sources()
    ai_pool = ai_defaults.provider(provider)
    default_model = (
        ai_pool.default_model
        if ai_pool is not None
        else str(info.get("default_model", ""))
    )
    return {
        "api_key": keys[0] if keys else "",
        "api_keys": keys,
        "base_url": base_url or provider_base_url(info),
        "model": model or default_model,
        "fallback_models": ai_defaults.fallback_models,
    }


def _load_env_line(line: str) -> None:
    text = line.strip()
    if not text or text.startswith("#") or "=" not in text:
        return
    key, value = text.split("=", 1)
    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def _configured_env_key_values() -> tuple[str, ...]:
    """Return resolved secret values for every env_key declared in PROVIDERS.

    The keys are *references* to where secrets live (e.g.
    ``GROQ_API_KEY_1``), not AI configuration. Secrets continue to be
    loaded from the OS environment via the ``.env`` loader — this
    helper just enumerates them so the rotation layer can iterate.
    """
    keys = [key for info in PROVIDERS.values() for key in info.get("env_keys", ())]
    return tuple(value for value in (os.getenv(key, "") for key in keys) if value)


def _configured_keys_for(env_keys: tuple[str, ...]) -> tuple[str, ...]:
    """Return non-empty secret values for a specific provider's env_keys.

    Same intent as :func:`_configured_env_key_values` but scoped to a
    single provider's declared env_keys (so we don't leak other
    providers' secrets into the rotation plan).
    """
    return tuple(
        value for value in (os.getenv(key, "").strip() for key in env_keys)
        if value
    )


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
    "_configured_keys_for",
    "_dedupe",
]
