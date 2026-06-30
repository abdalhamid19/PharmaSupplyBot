"""Core functions and models for AI provider/model rotation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .ai_health import split_csv, dedupe, mask_key
from .ai_rotation_config import PROVIDER_ORDER, DEFAULT_MODELS
from ..config import PROVIDERS, cloudflare_base_url, provider_base_url


@dataclass(frozen=True, slots=True)
class AIModelAttempt:
    """Single AI provider/model attempt configuration for rotation."""

    provider: str
    base_url: str
    key_name: str
    api_key: str = field(repr=False)
    model: str
    quality_rank: int
    latency: float = 9999.0
    quota_remaining: float = 0.0
    eligible: bool = True
    disabled_until: str = ""
    rotation_tier: int = 1

    @property
    def key_suffix(self) -> str:
        return self.api_key[-6:] if self.api_key else ""

    @property
    def key_masked(self) -> str:
        return mask_key(self.api_key)

    def safe_tuple(self) -> tuple[str, str, str]:
        return self.provider, self.key_suffix, self.model


def _provider_keys(provider: str, info: dict) -> list[tuple[str, str]]:
    keys = []
    for env_name in info.get("env_keys", ()):
        value = os.getenv(env_name, "").strip()
        if value:
            keys.append((env_name, value))
    seen = set()
    out = []
    for item in keys:
        if item[1] not in seen:
            seen.add(item[1])
            out.append(item)
    return out


def _provider_models(provider: str, info: dict) -> list[str]:
    env_name = f"{provider.upper()}_MODELS"
    env_models = split_csv(os.getenv(env_name, ""))
    defaults = list(DEFAULT_MODELS.get(provider, ()))
    if not defaults and info.get("default_model"):
        defaults = [info["default_model"]]
    return dedupe(env_models + defaults)


def _model_tier(rank: int, model_count: int) -> int:
    if model_count <= 0:
        return 3
    first_end = (model_count + 2) // 3
    second_end = (model_count * 2 + 2) // 3
    if rank <= first_end:
        return 1
    if rank <= second_end:
        return 2
    return 3


def _cloudflare_account_ids(info: dict) -> dict[str, str]:
    account_id_envs = info.get("account_id_envs", ())
    return {
        key_env: os.getenv(account_env, "").strip()
        for key_env, account_env in zip(info.get("env_keys", ()), account_id_envs)
        if os.getenv(account_env, "").strip()
    }


def _provider_base_url(provider: str, info: dict, key_name: str) -> str:
    if provider == "cloudflare":
        account_id = _cloudflare_account_ids(info).get(key_name, "")
        if account_id:
            return cloudflare_base_url(account_id)
    return provider_base_url(info)


def _provider_attempts(provider: str) -> list[AIModelAttempt]:
    info = PROVIDERS.get(provider, {})
    keys = _provider_keys(provider, info)
    models = _provider_models(provider, info)
    attempts = []
    model_count = len(models)
    for key_name, key_value in keys:
        base_url = _provider_base_url(provider, info, key_name)
        if not base_url:
            continue
        for rank, model in enumerate(models, start=1):
            attempts.append(
                AIModelAttempt(
                    provider=provider,
                    base_url=base_url,
                    key_name=key_name,
                    api_key=key_value,
                    model=model,
                    quality_rank=rank,
                    rotation_tier=_model_tier(rank, model_count),
                )
            )
    return attempts


def configured_attempts(providers: str = "auto") -> tuple[AIModelAttempt, ...]:
    """Return configured AI attempts for specified providers or all by default."""
    selected = _selected_providers(providers)
    attempts: list[AIModelAttempt] = []
    for provider in selected:
        attempts.extend(_provider_attempts(provider))
    return tuple(rank_attempts(attempts))


def rank_attempts(attempts) -> list[AIModelAttempt]:
    """Rank AI attempts by balanced sorting key for optimal rotation order."""
    return sorted(attempts, key=_balanced_sort_key)


def _balanced_sort_key(attempt: AIModelAttempt):
    quota_sort = -attempt.quota_remaining if attempt.quota_remaining else 0
    return (
        not attempt.eligible,
        bool(attempt.disabled_until),
        attempt.rotation_tier,
        attempt.quality_rank,
        quota_sort,
        attempt.latency,
        PROVIDER_ORDER.index(attempt.provider)
        if attempt.provider in PROVIDER_ORDER else len(PROVIDER_ORDER),
    )


def _selected_providers(value: str) -> tuple[str, ...]:
    if not value or value == "auto":
        return PROVIDER_ORDER
    requested = tuple(p.strip() for p in value.split(",") if p.strip())
    return tuple(p for p in requested if p in PROVIDERS and p != "rotation")


__all__ = [
    "AIModelAttempt",
    "configured_attempts",
    "rank_attempts",
]
