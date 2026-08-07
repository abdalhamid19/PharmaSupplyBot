"""Core functions and models for AI provider/model rotation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .ai_health import split_csv, dedupe, mask_key
from .ai_rotation_config import PROVIDER_ORDER
from ..config import (
    PROVIDERS,
    AIConfig,
    ProviderMetadata,
    cloudflare_base_url,
    get_provider_metadata,
    provider_base_url,
)


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


def _resolve_meta(provider: str) -> ProviderMetadata | None:
    """Return the resolved :class:`ProviderMetadata` for ``provider``.

    Falls back to the legacy :data:`PROVIDERS` dict only when the YAML
    layer does not declare the provider — preserved for environments
    that haven't migrated ``state/config.yaml`` yet.
    """
    meta = get_provider_metadata(provider)
    if meta is not None and (meta.base_url or meta.env_keys or meta.account_id_env):
        return meta
    legacy = PROVIDERS.get(provider)
    if not legacy:
        return None
    # Synthesise a ProviderMetadata from the legacy dict shape so the
    # downstream helpers can treat both layers uniformly.
    env_keys = legacy.get("env_keys", ())
    return ProviderMetadata(
        name=provider,
        base_url=str(legacy.get("base_url", "")),
        env_keys=tuple(env_keys) if isinstance(env_keys, (list, tuple)) else (),
        account_id_env=str(legacy.get("account_id_env", "")),
    )


def _provider_keys(
    meta: ProviderMetadata, account_id_envs: tuple[str, ...] = ()
) -> list[tuple[str, str]]:
    """Read API keys for the provider.

    ``account_id_envs`` is the optional parallel tuple of env-var names
    that supply the per-key account id (Cloudflare only). When non-empty,
    the two tuples are zipped — keys without an account id are skipped.
    """
    keys: list[tuple[str, str]] = []
    env_keys = list(meta.env_keys)
    if account_id_envs:
        for env_name, account_env in zip(env_keys, account_id_envs):
            value = os.getenv(env_name, "").strip()
            if value and os.getenv(account_env, "").strip():
                keys.append((env_name, value))
    else:
        for env_name in env_keys:
            value = os.getenv(env_name, "").strip()
            if value:
                keys.append((env_name, value))
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for item in keys:
        if item[1] not in seen:
            seen.add(item[1])
            out.append(item)
    return out


def _provider_models(provider: str, meta: ProviderMetadata) -> list[str]:
    """Return the rotation model list for ``provider``.

    Resolution order:
        1. ``ai.providers.{name}.models`` from YAML.
        2. ``meta.default_model`` (single-model fallback).
    """
    ai_pool = AIConfig.from_sources().provider(provider)
    if ai_pool is not None:
        return dedupe(list(ai_pool.models))
    # No YAML pool (e.g. provider declared with empty ``models``). Prefer
    # the metadata default when available, otherwise yield nothing so an
    # empty provider contributes zero attempts to the rotation plan.
    default_model = getattr(meta, "default_model", "") or getattr(
        meta, "default_model", ""
    )
    return [default_model] if default_model else []


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


def _cloudflare_account_id_envs() -> tuple[str, ...]:
    """Return the parallel-tuple env-var names for Cloudflare account IDs.

    Cloudflare keys are paired with their account IDs by index:
    ``CLOUDFLARE_API_TOKEN_1`` ↔ ``CLOUDFLARE_ACCOUNT_ID_1`` etc.
    """
    return (
        "CLOUDFLARE_ACCOUNT_ID_1",
        "CLOUDFLARE_ACCOUNT_ID_2",
        "CLOUDFLARE_ACCOUNT_ID_3",
        "CLOUDFLARE_ACCOUNT_ID_4",
        "CLOUDFLARE_ACCOUNT_ID_5",
        "CLOUDFLARE_ACCOUNT_ID_6",
        "CLOUDFLARE_ACCOUNT_ID",
    )


def _provider_base_url(
    provider: str,
    meta: ProviderMetadata,
    key_name: str,
    account_id_envs: tuple[str, ...] = (),
) -> str:
    """Resolve the per-attempt base URL.

    For Cloudflare, the URL is derived from the per-key account ID,
    not from the global ``meta.account_id_env`` (the latter is only
    a single fallback). When ``account_id_envs`` is non-empty, the
    function looks up the parallel account-id env-var for ``key_name``.
    """
    if provider == "cloudflare":
        if account_id_envs:
            # Find the account-id env paired with ``key_name``.
            try:
                idx = list(meta.env_keys).index(key_name)
            except ValueError:
                idx = -1
            if 0 <= idx < len(account_id_envs):
                account_id = os.getenv(account_id_envs[idx], "").strip()
                if account_id:
                    return cloudflare_base_url(account_id)
        # Final fallback: the legacy single-key env (CLOUDFLARE_ACCOUNT_ID).
        if meta.account_id_env:
            account_id = os.getenv(meta.account_id_env, "").strip()
            if account_id:
                return cloudflare_base_url(account_id)
    if meta.base_url:
        return meta.base_url
    # Fall through to the legacy helper for backward compatibility.
    return provider_base_url({"base_url": meta.base_url})


def _provider_attempts(provider: str) -> list[AIModelAttempt]:
    meta = _resolve_meta(provider)
    if meta is None:
        return []
    account_id_envs = (
        _cloudflare_account_id_envs() if provider == "cloudflare" else ()
    )
    keys = _provider_keys(meta, account_id_envs)
    models = _provider_models(provider, meta)
    attempts: list[AIModelAttempt] = []
    model_count = len(models)
    for key_name, key_value in keys:
        base_url = _provider_base_url(
            provider, meta, key_name, account_id_envs
        )
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
    # Allow ``PROVIDERS`` lookups for legacy callers; ``ProviderMetadata``
    # resolution is lazy and falls back to the dict anyway.
    return tuple(p for p in requested if p in PROVIDERS and p != "rotation")


__all__ = [
    "AIModelAttempt",
    "configured_attempts",
    "rank_attempts",
]
