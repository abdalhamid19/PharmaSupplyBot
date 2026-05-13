"""CLI helpers for live-order AI matching settings."""

from __future__ import annotations

import argparse

from ..core.drug_matching.ai_rotation import configured_attempts
from ..core.drug_matching.config import APIConfig, resolve_api_config
from ..core.order_ai_matching import OrderAiSettings


def order_ai_settings(args: argparse.Namespace) -> OrderAiSettings:
    """Build live-order AI settings from CLI flags."""
    concurrency = max(1, int(getattr(args, "concurrency", None) or 5))
    return OrderAiSettings(
        enabled=bool(getattr(args, "ai", False)),
        api_config=order_api_config(args),
        concurrency=concurrency,
        accept_confidence=float(getattr(args, "ai_accept_confidence", 0.9)),
        review_threshold=float(getattr(args, "ai_review_threshold", 0.95)),
        verify_policy=str(getattr(args, "ai_verify_policy", "score")),
        search_policy=str(getattr(args, "ai_search_policy", "review-candidates")),
    )


def order_api_config(args: argparse.Namespace) -> APIConfig:
    """Resolve AI API settings for live-order matching."""
    if getattr(args, "provider", None) == "rotation":
        return _rotation_api_config(args)
    resolved = resolve_api_config(
        getattr(args, "provider", None) or "",
        getattr(args, "model", None) or "",
        getattr(args, "api_key", None) or "",
    )
    return APIConfig(
        api_key=resolved["api_key"],
        api_keys=resolved.get("api_keys", ()),
        base_url=resolved["base_url"],
        model=resolved["model"],
        fallback_models=resolved.get("fallback_models", ()),
        review_model=getattr(args, "review_model", None) or "",
    )


def _rotation_api_config(args: argparse.Namespace) -> APIConfig:
    attempts = configured_attempts("auto")
    first = attempts[0] if attempts else None
    return APIConfig(
        api_key=first.api_key if first else "",
        api_keys=(first.api_key,) if first else (),
        base_url=first.base_url if first else "",
        model=first.model if first else "",
        review_model=getattr(args, "review_model", None) or "",
        attempt_plan=attempts,
    )
