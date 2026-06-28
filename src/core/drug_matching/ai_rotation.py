"""Provider/model rotation planning for AI calls."""
from __future__ import annotations

from .ai_rotation_config import PROVIDER_ORDER, DEFAULT_MODELS
from .ai_rotation_models import AIModelAttempt
from .ai_rotation_core import configured_attempts, rank_attempts
from .ai_rotation_providers import (
    _provider_keys,
    _provider_models,
    _model_tier,
    _cloudflare_account_ids,
    _provider_base_url,
    _provider_attempts,
)
from .ai_rotation_core import _balanced_sort_key, _selected_providers


# Backward compatibility: redirect to refactored modules
def configured_attempts(providers: str = "auto") -> tuple[AIModelAttempt, ...]:
    from .ai_rotation_core import configured_attempts as _fn
    return _fn(providers)


def rank_attempts(attempts) -> list[AIModelAttempt]:
    from .ai_rotation_core import rank_attempts as _fn
    return _fn(attempts)


def _balanced_sort_key(attempt: AIModelAttempt):
    from .ai_rotation_core import _balanced_sort_key as _fn
    return _fn(attempt)


def _selected_providers(value: str) -> tuple[str, ...]:
    from .ai_rotation_core import _selected_providers as _fn
    return _fn(value)


def _provider_attempts(provider: str) -> list[AIModelAttempt]:
    from .ai_rotation_providers import _provider_attempts as _fn
    return _fn(provider)


def _model_tier(rank: int, model_count: int) -> int:
    from .ai_rotation_providers import _model_tier as _fn
    return _fn(rank, model_count)


def _cloudflare_account_ids(info: dict) -> dict[str, str]:
    from .ai_rotation_providers import _cloudflare_account_ids as _fn
    return _fn(info)


def _provider_base_url(provider: str, info: dict, key_name: str) -> str:
    from .ai_rotation_providers import _provider_base_url as _fn
    return _fn(provider, info, key_name)


def _provider_keys(provider: str, info: dict) -> list[tuple[str, str]]:
    from .ai_rotation_providers import _provider_keys as _fn
    return _fn(provider, info)


def _provider_models(provider: str, info: dict) -> list[str]:
    from .ai_rotation_providers import _provider_models as _fn
    return _fn(provider, info)
