"""Payload and result building functions for AI health tests."""

from __future__ import annotations

from typing import Any

from .ai_health_utils import mask_key


def build_payload(model: str, mode: str, max_tokens: int) -> dict[str, Any]:
    """Build test payload for API request."""
    from .ai_health_test_constants import TEST_MESSAGES
    payload = {
        "model": model,
        "messages": TEST_MESSAGES,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if mode == "json":
        payload["response_format"] = {"type": "json_object"}
    return payload


def empty_result(key, model: str, mode: str, base_url: str) -> dict[str, Any]:
    """Create empty result template."""
    return {
        "key_name": key.name,
        "key_masked": mask_key(key.value),
        "model": model,
        "mode": mode,
        "base_url": base_url,
        "http_status": "",
        "elapsed_s": "",
        "ok": False,
        "json_ok": False,
        "schema_ok": False,
        "is_correct": "",
        "confidence": "",
        "error_type": "",
        "error_message": "",
        "content_excerpt": "",
        "raw_excerpt": "",
        "quota_limit_minute": "",
        "quota_remaining_minute": "",
        "quota_reset_minute": "",
        "quota_reset_minute_in": "",
        "quota_limit_day": "",
        "quota_remaining_day": "",
        "quota_reset_day": "",
        "quota_reset_day_in": "",
        "rate_limit_requests": "",
        "rate_remaining_requests": "",
        "rate_reset_requests": "",
        "rate_reset_requests_in": "",
        "rate_limit_tokens": "",
        "rate_remaining_tokens": "",
        "rate_reset_tokens": "",
        "rate_reset_tokens_in": "",
        "retry_after": "",
        "retry_after_in": "",
        "quota_reset_in": "",
        "rate_headers": "",
    }


__all__ = ["build_payload", "empty_result"]
