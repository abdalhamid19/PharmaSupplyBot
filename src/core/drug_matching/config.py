"""Configuration models for component-aware drug matching and AI review."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pharmasupplybot.matching")
ROOT_DIR = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class MatchingConfig:
    """Thresholds used by the indexed drug matcher."""

    fuzzy_threshold: int = 80
    brand_prefix_min: int = 4
    brand_prefix_ratio: float = 0.75
    ai_verify_threshold: float = 90.0
    ai_batch_size: int = 20
    ai_max_concurrent: int = 5
    top_k_candidates: int = 10
    ai_review_threshold: float = 0.8
    ai_search_limit: int | None = None
    ai_verify_policy: str = "score"
    ai_verify_limit: int | None = None
    ai_search_policy: str = "review-candidates"
    ai_search_min_candidate_score: float = 80.0
    ai_search_accept_confidence: float = 0.75
    ai_search_candidate_limit: int = 5
    ai_search_review_candidate_min_score: float = 68.0
    ai_search_review_candidate_limit: int = 8
    ai_search_review_accept_confidence: float = 0.85
    ai_search_allow_component_mismatch_reasons: tuple[str, ...] = (
        "different_brand",
        "brand_prefix_mismatch",
        "different_import_status",
        "different_modifier",
        "different_quantity",
        "different_volume",
    )


PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "env_keys": ("OPENROUTER_API_KEY_1", "OPENROUTER_API_KEY"),
        "default_model": "openai/gpt-4o-mini",
    },
    "opencode": {
        "base_url": "https://opencode.ai/zen/v1",
        "env_key": "OPENCODE_API_KEY",
        "env_keys": ("OPENCODE_API_KEY_1", "OPENCODE_API_KEY"),
        "default_model": "big-pickle",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "env_keys": ("GROQ_API_KEY_1", "GROQ_API_KEY"),
        "default_model": "openai/gpt-oss-120b",
    },
    "github": {
        "base_url": "https://models.github.ai/inference",
        "env_key": "GITHUB_API_KEY",
        "env_keys": ("GITHUB_API_KEY_1", "GITHUB_API_KEY"),
        "default_model": "openai/gpt-4.1-mini",
    },
    "cloudflare": {
        "base_url": "",
        "base_url_env": "CLOUDFLARE_BASE_URL",
        "account_id_env": "CLOUDFLARE_ACCOUNT_ID",
        "env_key": "CLOUDFLARE_API_TOKEN",
        "env_keys": ("CLOUDFLARE_API_TOKEN_1", "CLOUDFLARE_API_TOKEN"),
        "default_model": "@cf/openai/gpt-oss-120b",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "env_keys": ("CEREBRAS_API_KEY_1", "CEREBRAS_API_KEY"),
        "default_model": "gpt-oss-120b",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GOOGLE_API_KEY",
        "env_keys": ("GOOGLE_API_KEY_1", "GOOGLE_API_KEY"),
        "default_model": "gemini-2.5-flash",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "env_keys": ("MISTRAL_API_KEY_1", "MISTRAL_API_KEY"),
        "default_model": "mistral-small-latest",
    },
    "rotation": {"base_url": "", "env_key": "", "env_keys": (), "default_model": ""},
    "custom": {
        "base_url": "",
        "env_key": "CUSTOM_API_KEY",
        "env_keys": ("CUSTOM_API_KEY",),
        "default_model": "",
    },
}


@dataclass(frozen=True)
class APIConfig:
    """AI API settings for verification, search, and model rotation."""

    api_key: str = ""
    api_keys: tuple[str, ...] = ()
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"
    fallback_models: tuple[str, ...] = ()
    review_model: str = ""
    healthy_combos: tuple = ()
    attempt_plan: tuple = ()
    review_attempt_plan: tuple = ()
    max_tokens: int = 1024
    temperature: float = 0.1


@dataclass(frozen=True)
class Paths:
    """Default CSV paths for standalone product matching."""

    drugs_csv: Path = field(default_factory=lambda: ROOT_DIR / "data/input/order_items")
    tawreed_csv: Path = field(
        default_factory=lambda: ROOT_DIR / "artifacts/wardany/tawreed_products.csv"
    )
    output_csv: Path = field(default_factory=lambda: _default_output_csv())
    env_file: Path = field(default_factory=lambda: ROOT_DIR / ".env")


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


def provider_base_url(info: dict) -> str:
    """Return a provider base URL, including Cloudflare account URL expansion."""
    account_id = os.getenv(info.get("account_id_env", ""), "").strip()
    if account_id:
        return cloudflare_base_url(account_id)
    url = os.getenv(info.get("base_url_env", ""), "").strip() or info["base_url"]
    return "" if "<" in url or ">" in url else url


def cloudflare_base_url(account_id: str) -> str:
    """Return the OpenAI-compatible Cloudflare Workers AI URL."""
    return f"https://api.cloudflare.com/client/v4/accounts/{account_id.strip()}/ai/v1"


def _provider_api_config(provider: str, model: str, api_key: str) -> dict:
    info = PROVIDERS[provider]
    keys = _dedupe((api_key, *(os.getenv(key, "") for key in info["env_keys"])))
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
        model.strip() for model in os.getenv("FALLBACK_MODELS", "").split(",")
        if model.strip()
    )


def _dedupe(values) -> tuple[str, ...]:
    seen = set()
    return tuple(value for value in values if value and value not in seen and not seen.add(value))


def _default_output_csv() -> Path:
    stem = datetime.now().strftime("matched_drugs_verified_%Y%m%d_%H%M%S.csv")
    return ROOT_DIR / "artifacts" / "matching" / stem
