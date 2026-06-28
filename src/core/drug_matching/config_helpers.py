"""Helper functions for configuration loading and resolution."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .config_models import Paths
from .config_providers import PROVIDERS

logger = logging.getLogger("pharmasupplybot.matching")


def setup_logging(level: str = "INFO") -> None:
    """Configure synchronous fallback logging for CLI execution."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_env(path: Path | None = None) -> None:
    """Load simple KEY=VALUE lines from the project .env file."""
    env_path = path or Paths().env_file
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        _load_env_line(line)


def resolve_api_config(provider: str = "", model: str = "", api_key: str = "") -> dict:
    """Resolve API settings from arguments and environment variables."""
    if provider and provider in PROVIDERS:
        return _provider_api_config(provider, model, api_key)
    keys = _configured_env_key_values()
    return {
        "api_key": api_key or os.getenv("OPENROUTER_API_KEY", ""),
        "api_keys": _dedupe((api_key, *keys)),
        "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "model": model or os.getenv("AI_MODEL", "openai/gpt-4o-mini"),
        "fallback_models": _fallback_models(),
    }


def _provider_api_config(provider: str, model: str, api_key: str) -> dict:
    info = PROVIDERS[provider]
    keys = _dedupe((api_key, *(os.getenv(key, "") for key in info["env_keys"])))
    from .config_providers import provider_base_url
    return {
        "api_key": keys[0] if keys else "",
        "api_keys": keys,
        "base_url": provider_base_url(info),
        "model": model or os.getenv("AI_MODEL", "") or info["default_model"],
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
    return tuple(
        model.strip()
        for model in os.getenv("FALLBACK_MODELS", "").split(",")
        if model.strip()
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
    "_fallback_models",
    "_dedupe",
]
