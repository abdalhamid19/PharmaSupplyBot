"""Reusable AI provider health checks."""
from __future__ import annotations

import asyncio
import csv
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp

from .config import PROVIDERS
from .verifier import _extract_json

OPENCODE_BASE_URL = PROVIDERS["opencode"]["base_url"]
OUT_DIR = Path("output/api_model_tests")

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


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def mask_key(key: str) -> str:
    return f"...{key[-6:]}" if key else ""


def _clean_header(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


def _duration_from_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def reset_in_text(value: Any, now: float | None = None) -> str:
    """Render common rate-limit reset header formats as a remaining duration."""
    raw = _clean_header(value)
    if not raw:
        return ""
    now = time.time() if now is None else now
    if raw.isdigit():
        number = float(raw)
        # Small values are usually delta seconds, large values are Unix time.
        seconds = number - now if number > 1_000_000_000 else number
        return _duration_from_seconds(seconds)
    try:
        return _duration_from_seconds(float(raw))
    except ValueError:
        pass
    try:
        reset_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        return _duration_from_seconds(reset_at.timestamp() - now)
    except ValueError:
        return raw


def _first_header(headers, names: list[str]) -> str:
    for name in names:
        value = headers.get(name)
        if value not in (None, ""):
            return _clean_header(value)
    return ""


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


def build_payload(model: str, mode: str, max_tokens: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": TEST_MESSAGES,
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    if mode == "json":
        payload["response_format"] = {"type": "json_object"}
    return payload


def content_from_response(data: Any) -> tuple[str, str]:
    try:
        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        return str(content or ""), ""
    except Exception as exc:  # noqa: BLE001 - diagnostics should report type.
        return "", f"{type(exc).__name__}: {exc}"


def validate_model_json(content: str) -> tuple[bool, str, dict[str, Any] | None]:
    parsed = _extract_json(content)
    if parsed is None:
        return False, "invalid_json", None
    required = {"is_correct", "reason", "confidence"}
    missing = sorted(required - set(parsed))
    if missing:
        return False, f"missing_fields:{','.join(missing)}", parsed
    return True, "ok", parsed


def empty_result(key: AIKey, model: str, mode: str, base_url: str) -> dict[str, Any]:
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
    except Exception as exc:  # noqa: BLE001 - report exact runtime failure.
        result["error_type"] = type(exc).__name__
        result["error_message"] = str(exc)[:300]
        return result
    finally:
        result["elapsed_s"] = round(time.perf_counter() - started, 3)


async def _handle_response(resp, result: dict[str, Any]) -> dict[str, Any]:
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


def _apply_error_quota_hints(text: str, result: dict[str, Any]) -> None:
    """Infer quota reset from provider error body when headers are sparse."""
    if "FreeUsageLimitError" not in text:
        return
    retry_after = result.get("retry_after", "")
    retry_after_in = result.get("retry_after_in", "")
    if retry_after and not result.get("quota_reset_day"):
        result["quota_reset_day"] = retry_after
        result["quota_reset_day_in"] = retry_after_in
    if retry_after_in and not result.get("quota_reset_in"):
        result["quota_reset_in"] = retry_after_in
    if not result.get("quota_remaining_day"):
        result["quota_remaining_day"] = "0"


def _validate_content(content: str, result: dict[str, Any]) -> dict[str, Any]:
    schema_ok, reason, parsed = validate_model_json(content)
    result["json_ok"] = parsed is not None
    result["schema_ok"] = schema_ok
    if parsed:
        result["is_correct"] = parsed.get("is_correct", "")
        result["confidence"] = parsed.get("confidence", "")
    if not schema_ok:
        result["error_type"] = reason
        result["error_message"] = content[:300].replace("\n", " ")
        return result
    result["ok"] = True
    return result


async def run_health_checks(
    keys: list[AIKey],
    models: list[str],
    modes: list[str],
    timeout_s: float = 20.0,
    max_tokens: int = 256,
    concurrency: int = 4,
    base_url: str = OPENCODE_BASE_URL,
) -> list[dict[str, Any]]:
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


def healthy_combos(rows: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    combos = []
    seen = set()
    for row in rows:
        if not row.get("ok") or row.get("mode") != "json":
            continue
        combo = (str(row["key_masked"])[-6:], str(row["model"]))
        if combo not in seen:
            seen.add(combo)
            combos.append(combo)
    return tuple(combos)


def write_reports(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUT_DIR / f"opencode_model_test_{stamp}.csv"
    json_path = OUT_DIR / f"opencode_model_test_{stamp}.json"
    if not rows:
        rows = [empty_result(AIKey("", ""), "", "", OPENCODE_BASE_URL)]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return csv_path, json_path
