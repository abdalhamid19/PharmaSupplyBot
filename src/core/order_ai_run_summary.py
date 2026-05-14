"""Summaries for order AI trace artifacts."""

from __future__ import annotations

from collections import Counter


def summarize_order_ai_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Return compact grouped counts for order AI trace rows."""
    counters = {
        "phase": Counter(_value(row, "phase") for row in rows),
        "ai_status": Counter(_value(row, "ai_status") for row in rows),
        "provider_error": Counter(_provider_error_key(row) for row in rows if _is_error(row)),
    }
    return [
        {"group": group, "value": value, "count": count}
        for group, counter in counters.items()
        for value, count in counter.most_common()
        if value
    ]


def _is_error(row: dict[str, str]) -> bool:
    return _value(row, "phase").startswith("api_attempt") and _value(row, "decision") != "success"


def _provider_error_key(row: dict[str, str]) -> str:
    provider = _value(row, "provider_used") or _value(row, "provider")
    status = _value(row, "status")
    error_code = _value(row, "error_code")
    return " / ".join(value for value in (provider, status, error_code) if value)


def _value(row: dict[str, str], key: str) -> str:
    return str(row.get(key) or "").strip()
