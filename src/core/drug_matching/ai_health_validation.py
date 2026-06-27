"""Response validation functions for AI health checks."""

import json
from typing import Any

from .verifier import extract_json


def content_from_response(data: Any) -> tuple[str, str]:
    """Extract content from API response."""
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
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def validate_model_json(content: str) -> tuple[bool, str, dict[str, Any] | None]:
    """Validate model JSON response."""
    parsed = extract_json(content)
    if parsed is None:
        return False, "invalid_json", None
    required = {"is_correct", "reason", "confidence"}
    missing = sorted(required - set(parsed))
    if missing:
        return False, f"missing_fields:{','.join(missing)}", parsed
    return True, "ok", parsed


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
    """Validate content and update result."""
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


__all__ = [
    "content_from_response",
    "validate_model_json",
    "_apply_error_quota_hints",
    "_validate_content",
]
