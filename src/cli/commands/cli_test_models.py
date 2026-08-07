"""CLI command runner to live-test every configured AI model.

Sends one real ``chat/completions`` probe per (provider, model) pair —
using the same resolution as the rotation plan (``configured_attempts``)
and the same probe as the health layer (``execute_one``) — then reports:

* which models work and which fail,
* per-model latency (``elapsed_s``),
* the exact failure cause (HTTP status + error type + message excerpt).

Results are also written to ``output/api_model_tests/ai_models_test_*.{csv,json}``.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

from src.core.config.config_models import AppConfig
from src.core.drug_matching.ai.ai_health_report import OUT_DIR
from src.core.drug_matching.ai.ai_health_test_constants import AIKey
from src.core.drug_matching.ai.ai_health_test_execution import execute_one
from src.core.drug_matching.ai.ai_rotation import (
    AIModelAttempt,
    configured_attempts,
)
from src.core.drug_matching.ai.ai_rotation_health_status import health_status
from ..presenter import FormatFlags, render_summary, render_table
from ..registry import register

__all__ = ["run_test_models_command"]


@register("test-models")
def run_test_models_command(app_config: AppConfig, args: argparse.Namespace) -> int:
    """Probe all configured AI models live and print a status/latency report."""
    provider = getattr(args, "provider", None)
    providers = (
        provider.strip()
        if isinstance(provider, str) and provider.strip()
        else "auto"
    )
    timeout_s = float(getattr(args, "timeout", 25.0))
    max_tokens = int(getattr(args, "max_tokens", 64))
    concurrency = max(1, int(getattr(args, "concurrency", 6)))
    all_keys = bool(getattr(args, "all_keys", False))

    attempts = list(configured_attempts(providers))
    if not all_keys:
        attempts = _unique_model_attempts(attempts)

    fmt = FormatFlags.resolve(explicit=getattr(args, "format", None))
    if not attempts:
        print(render_summary(
            "test-models",
            {"tested": 0, "reason": "no configured attempts (missing API keys?)"},
            fmt,
            success=False,
        ))
        return 1

    rows = asyncio.run(_run_checks(attempts, timeout_s, max_tokens, concurrency))
    for row in rows:
        row["health"] = health_status(row)
    rows.sort(key=_sort_key)

    print(render_table(
        [_display_row(r) for r in rows],
        ["provider", "model", "status", "health", "latency_s", "http", "reason"],
        fmt,
    ))

    csv_path, json_path = _write_reports(rows)

    ok_count = sum(1 for r in rows if r.get("ok"))
    print(render_summary(
        "test-models",
        {
            "tested": len(rows),
            "working": ok_count,
            "failing": len(rows) - ok_count,
            "csv_report": str(csv_path),
            "json_report": str(json_path),
        },
        fmt,
        success=ok_count > 0,
    ))
    return 0 if ok_count else 1


def _unique_model_attempts(attempts: list[AIModelAttempt]) -> list[AIModelAttempt]:
    """Keep the first attempt per (provider, model) — one probe per model."""
    seen: set[tuple[str, str]] = set()
    out: list[AIModelAttempt] = []
    for attempt in attempts:
        key = (attempt.provider, attempt.model)
        if key in seen:
            continue
        seen.add(key)
        out.append(attempt)
    return out


async def _run_checks(
    attempts: list[AIModelAttempt],
    timeout_s: float,
    max_tokens: int,
    concurrency: int,
) -> list[dict[str, Any]]:
    connector = aiohttp.TCPConnector(limit=concurrency)
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:

        async def guarded(attempt: AIModelAttempt) -> dict[str, Any]:
            async with sem:
                row = await execute_one(
                    session,
                    AIKey(name=attempt.key_name, value=attempt.api_key),
                    attempt.model,
                    mode="json",
                    timeout_s=timeout_s,
                    max_tokens=max_tokens,
                    base_url=attempt.base_url,
                )
            row["provider"] = attempt.provider
            row["rotation_tier"] = attempt.rotation_tier
            return row

        return await asyncio.gather(*(guarded(a) for a in attempts))


def _sort_key(row: dict[str, Any]):
    return (
        not bool(row.get("ok")),
        float(row.get("elapsed_s") or 9999),
        str(row.get("provider", "")),
        str(row.get("model", "")),
    )


def _reason(row: dict[str, Any]) -> str:
    """Exact failure cause: error type + message excerpt (empty when OK)."""
    if row.get("ok"):
        return ""
    error_type = str(row.get("error_type") or "unknown")
    message = str(row.get("error_message") or "").replace("\n", " ").strip()
    if len(message) > 160:
        message = message[:157] + "..."
    return f"{error_type}: {message}" if message else error_type


def _display_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": row.get("provider"),
        "model": row.get("model"),
        "status": "OK" if row.get("ok") else "FAIL",
        "health": row.get("health"),
        "latency_s": row.get("elapsed_s"),
        "http": row.get("http_status"),
        "reason": _reason(row),
    }


def _write_reports(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    """Write full probe results to stamped CSV + JSON under OUT_DIR."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = OUT_DIR / f"ai_models_test_{stamp}.csv"
    json_path = OUT_DIR / f"ai_models_test_{stamp}.json"
    fieldnames = list(rows[0]) if rows else ["provider", "model", "ok"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return csv_path, json_path
