"""Provider-specific functions for AI rotation."""

from __future__ import annotations

import os

from .ai_health import split_csv, dedupe
from .ai_rotation_config import DEFAULT_MODELS
from .config import PROVIDERS, cloudflare_base_url, provider_base_url


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


def _provider_attempts(provider: str) -> list:
    from .ai_rotation_models import AIModelAttempt
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
