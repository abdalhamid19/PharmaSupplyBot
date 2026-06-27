"""Test execution functions for AI health checks."""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from .config import PROVIDERS
from .ai_health_utils import mask_key
from .ai_health_quota import extract_quota_headers
from .ai_health_validation import (
    content_from_response,
    validate_model_json,
    _apply_error_quota_hints,
    _validate_content,
)

OPENCODE_BASE_URL = PROVIDERS["opencode"]["base_url"]

TEST_MESSAGES = [
    {
        "role": "system",
        "content": (
            "Return JSON only. You verify whether two drug product names are "
            "the same sellable product."
        ),
    },
    {
        "role": "user",
        "content": (
            'Are these the same product? A="PANADOL 20 TAB", '
            'B="PANADOL 20 TABLETS". Return exactly: '
            '{"is_correct": true, "reason": "brief", "confidence": 0.0-1.0}'
        ),
    },
]


@dataclass(frozen=True, slots=True)
class AIKey:
    name: str
    value: str


def build_payload(model: str, mode: str, max_tokens: int) -> dict[str, Any]:
    """Build test payload for API request."""
    payload = {
        "model": model,
        "messages": TEST_MESSAGES,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if mode == "json":
        payload["response_format"] = {"type": "json_object"}
    return payload


def empty_result(key: AIKey, model: str, mode: str, base_url: str) -> dict[str, Any]:
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


async def test_one(
    session: aiohttp.ClientSession,
    key: AIKey,
    model: str,
    mode: str,
    timeout_s: float,
    max_tokens: int,
    base_url: str = OPENCODE_BASE_URL,
) -> dict[str, Any]:
    """Test one AI provider key/model combination."""
    started = time.perf_counter()
    result = empty_result(key, model, mode, base_url)
    headers = {
        "Authorization": f"Bearer {key.value}",
        "Content-Type": "application/json",
    }
    payload = build_payload(model, mode, max_tokens)
    try:
        async with session.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout_s),
        ) as resp:
            return await _handle_response(resp, result)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)[:300]
        return result
    finally:
        result["elapsed_s"] = round(time.perf_counter() - started, 3)


async def _handle_response(resp, result: dict[str, Any]) -> dict[str, Any]:
    """Handle API response and extract quota headers."""
    result["http_status"] = resp.status
    result.update(extract_quota_headers(resp.headers))
    text = await resp.text()
    result["raw_excerpt"] = text[:500].replace("\n", "\\n")
    _apply_error_quota_hints(text, result)
    if resp.status != 200:
        result["error_type"] = f"http_{resp.status}"
        result["error_message"] = text[:300].replace("\n", " ")
        return result
    try:
        import json
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        result["error_type"] = "response_not_json"
        result["error_message"] = str(exc)
        return result
    content, content_error = content_from_response(data)
    result["content_excerpt"] = content[:500].replace("\n", "\\n")
    if content_error:
        result["error_type"] = "response_shape"
        result["error_message"] = content_error
        return result
    return _validate_content(content, result)


async def run_health_checks(
    keys: list[AIKey],
    models: list[str],
    modes: list[str],
    timeout_s: float = 20.0,
    max_tokens: int = 256,
    concurrency: int = 4,
    base_url: str = OPENCODE_BASE_URL,
) -> list[dict[str, Any]]:
    """Run health checks for all key/model/mode combinations."""
    connector = aiohttp.TCPConnector(limit=concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        sem = asyncio.Semaphore(concurrency)

        async def guarded(key: AIKey, model: str, mode: str):
            async with sem:
                return await test_one(
                    session, key, model, mode,
                    timeout_s, max_tokens, base_url,
                )

        tasks = [
            guarded(key, model, mode)
            for key in keys
            for model in models
            for mode in modes
        ]
        return await asyncio.gather(*tasks)


__all__ = [
    "AIKey",
    "build_payload",
    "empty_result",
    "test_one",
    "run_health_checks",
]
