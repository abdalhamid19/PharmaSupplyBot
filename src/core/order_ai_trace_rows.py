"""Detailed AI trace rows for order artifacts."""
from __future__ import annotations
import json


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
