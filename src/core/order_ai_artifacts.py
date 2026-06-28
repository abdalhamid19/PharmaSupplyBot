"""Artifacts helpers for order AI trace and summary outputs."""

from __future__ import annotations
import json


def summarize_order_ai_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """Return compact grouped counts for order AI trace rows."""
    from collections import Counter
    
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


def order_ai_trace_rows(item, outcome) -> list[dict[str, object]]:
    """Return detailed AI trace rows for one item outcome."""
    if outcome is None:
        return []
    rows = [_ai_result_row(item, outcome, "ai_final", {})]
    rows.extend(_ai_phase_rows(item, outcome))
    rows.extend(_api_attempt_rows(item, outcome))
    return rows


def _ai_phase_rows(item, outcome) -> list[dict[str, object]]:
    return [
        _ai_result_row(item, outcome, phase, result)
        for phase, result in (
            ("ai_verify", outcome.verify_result),
            ("ai_search", outcome.search_result),
            ("ai_review", outcome.review_result),
        )
        if result
    ]


def _ai_result_row(item, outcome, phase: str, result: dict) -> dict[str, object]:
    return {
        "phase": phase,
        "item_code": item.code,
        "item_name": item.name,
        "ai_status": outcome.status,
        "result": _result_label(result),
        "confidence": result.get("confidence", outcome.confidence),
        "model_used": result.get("model_used", ""),
        "provider_used": result.get("provider_used", ""),
        "reason": result.get("reason", outcome.reason),
        "manual_review_required": outcome.manual_review,
    }


def _api_attempt_rows(item, outcome) -> list[dict[str, object]]:
    return [
        {"phase": phase, "item_code": item.code, "item_name": item.name, **attempt}
        for phase, result in _result_items(outcome)
        for attempt in result.get("_api_attempts", [])
    ]


def _result_items(outcome):
    return (
        ("api_attempt_verify", outcome.verify_result or {}),
        ("api_attempt_search", outcome.search_result or {}),
        ("api_attempt_review", outcome.review_result or {}),
    )


def _result_label(result: dict) -> str:
    return json.dumps(result.get("_raw", result), ensure_ascii=False, default=str)[:500]


__all__ = [
    "summarize_order_ai_rows",
    "order_ai_trace_rows",
]
