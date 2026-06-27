"""Quota header extraction for AI health checks."""

import json
from typing import Any

from .ai_health_utils import _first_header, reset_in_text


def extract_quota_headers(headers) -> dict[str, str]:
    """Capture provider rate-limit headers without assuming one exact schema."""
    minute_limit = _first_header(headers, [
        "x-ratelimit-limit-requests-minute",
        "x-ratelimit-limit-minute",
        "x-rpm-limit",
        "x-ratelimit-limit-rpm",
    ])
    minute_remaining = _first_header(headers, [
        "x-ratelimit-remaining-requests-minute",
        "x-ratelimit-remaining-minute",
        "x-rpm-remaining",
        "x-ratelimit-remaining-rpm",
    ])
    minute_reset = _first_header(headers, [
        "x-ratelimit-reset-requests-minute",
        "x-ratelimit-reset-minute",
        "x-rpm-reset",
        "x-ratelimit-reset-rpm",
    ])
    day_limit = _first_header(headers, [
        "x-ratelimit-limit-requests-day",
        "x-ratelimit-limit-day",
        "x-rpd-limit",
        "x-daily-limit",
    ])
    day_remaining = _first_header(headers, [
        "x-ratelimit-remaining-requests-day",
        "x-ratelimit-remaining-day",
        "x-rpd-remaining",
        "x-daily-remaining",
    ])
    day_reset = _first_header(headers, [
        "x-ratelimit-reset-requests-day",
        "x-ratelimit-reset-day",
        "x-rpd-reset",
        "x-daily-reset",
    ])
    request_limit = _first_header(headers, [
        "x-ratelimit-limit-requests",
        "ratelimit-limit",
        "x-ratelimit-limit",
    ])
    request_remaining = _first_header(headers, [
        "x-ratelimit-remaining-requests",
        "ratelimit-remaining",
        "x-ratelimit-remaining",
    ])
    request_reset = _first_header(headers, [
        "x-ratelimit-reset-requests",
        "ratelimit-reset",
        "x-ratelimit-reset",
    ])
    token_limit = _first_header(headers, ["x-ratelimit-limit-tokens"])
    token_remaining = _first_header(headers, ["x-ratelimit-remaining-tokens"])
    token_reset = _first_header(headers, ["x-ratelimit-reset-tokens"])
    retry_after = _first_header(headers, ["retry-after"])
    best_reset = day_reset or minute_reset or request_reset or retry_after
    rate_headers = {
        str(k).lower(): str(v)
        for k, v in headers.items()
        if "rate" in str(k).lower() or "quota" in str(k).lower()
        or str(k).lower() in {"retry-after"}
    }
    return {
        "quota_limit_minute": minute_limit,
        "quota_remaining_minute": minute_remaining,
        "quota_reset_minute": minute_reset,
        "quota_reset_minute_in": reset_in_text(minute_reset),
        "quota_limit_day": day_limit,
        "quota_remaining_day": day_remaining,
        "quota_reset_day": day_reset,
        "quota_reset_day_in": reset_in_text(day_reset),
        "rate_limit_requests": request_limit,
        "rate_remaining_requests": request_remaining,
        "rate_reset_requests": request_reset,
        "rate_reset_requests_in": reset_in_text(request_reset),
        "rate_limit_tokens": token_limit,
        "rate_remaining_tokens": token_remaining,
        "rate_reset_tokens": token_reset,
        "rate_reset_tokens_in": reset_in_text(token_reset),
        "retry_after": retry_after,
        "retry_after_in": reset_in_text(retry_after),
        "quota_reset_in": reset_in_text(best_reset),
        "rate_headers": json.dumps(rate_headers, ensure_ascii=False),
    }


__all__ = ["extract_quota_headers"]
