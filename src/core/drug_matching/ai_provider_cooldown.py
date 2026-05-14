"""Per-run provider cooldown for noisy AI rotation attempts."""
from __future__ import annotations

from typing import Any

COOLDOWN_ERRORS = frozenset({"rate_limited", "invalid_json", "null_content"})
DEFAULT_THRESHOLD = 2
_PROVIDER_FAILURES: dict[int, dict[str, int]] = {}


def apply_provider_cooldown(
    verifier: Any, result: dict[str, Any] | None, threshold: int = DEFAULT_THRESHOLD
) -> set[str]:
    """Disable providers with repeated rate-limit or parse failures."""
    if not isinstance(result, dict):
        return set()
    disabled: set[str] = set()
    counts = _PROVIDER_FAILURES.setdefault(id(verifier), {})
    for provider in _failed_attempt_providers(result.get("_api_attempts", [])):
        counts[provider] = counts.get(provider, 0) + 1
        if counts[provider] >= threshold:
            disabled.add(provider)
    for provider in disabled:
        _disable_provider(verifier, provider)
    if disabled:
        result["_provider_cooldown"] = ",".join(sorted(disabled))
    return disabled


def _failed_attempt_providers(attempts) -> list[str]:
    providers: list[str] = []
    for attempt in attempts or []:
        provider = str(attempt.get("provider", ""))
        if not provider or provider == "default":
            continue
        if str(attempt.get("error_code", "")) in COOLDOWN_ERRORS:
            providers.append(provider)
    return providers


def _disable_provider(verifier: Any, provider: str) -> None:
    failed = getattr(verifier, "_failed_combos", None)
    cfg = getattr(verifier, "_cfg", None)
    if failed is None or cfg is None:
        return
    for attempt in _configured_attempts(cfg):
        if getattr(attempt, "provider", "") != provider:
            continue
        failed.add((provider, getattr(attempt, "api_key", "")[-6:], attempt.model))


def _configured_attempts(cfg: Any) -> tuple:
    return tuple(getattr(cfg, "attempt_plan", ()) or ()) + tuple(
        getattr(cfg, "review_attempt_plan", ()) or ()
    )
