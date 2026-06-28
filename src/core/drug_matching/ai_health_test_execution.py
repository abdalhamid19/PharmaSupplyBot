"""Execution functions for AI health tests."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

from .ai_health_test_constants import AIKey, OPENCODE_BASE_URL
from .ai_health_test_payload import build_payload, empty_result
from .ai_health_quota import extract_quota_headers
from .ai_health_validation import (
    content_from_response,
    _apply_error_quota_hints,
    _validate_content,
)


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


__all__ = ["test_one", "run_health_checks"]
