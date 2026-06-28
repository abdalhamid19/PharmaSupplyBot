"""Health status classification and utilities for rotated AI attempts."""

_PERMANENT_FAILURES = {
    "permission-failed",
    "model-not-accessible",
}


def health_status(row: dict) -> str:
    if row.get("ok"):
        return "working"
    error_type = str(row.get("error_type", ""))
    http_status = str(row.get("http_status", ""))
    message = str(row.get("error_message", "")).lower()
    if error_type == "TimeoutError":
        return "degraded"
    if (
        error_type in {"invalid_json", "response_not_json", "response_shape", "null_content"}
        or "invalid_json" in error_type
        or error_type.startswith("missing_fields:")
    ):
        return "degraded"
    if http_status == "429" or error_type == "http_429":
        return "quota-limited"
    if http_status == "403" or error_type == "http_403":
        return "permission-failed"
    if (
        http_status == "404"
        or error_type == "http_404"
        or "model_not_found" in message
        or "does not exist" in message
        or "no such model" in message
    ):
        return "model-not-accessible"
    return "failed"


def fallback_tier(row: dict) -> int:
    return {
        "working": 0,
        "degraded": 1,
        "quota-limited": 2,
        "permission-failed": 3,
        "model-not-accessible": 4,
        "failed": 5,
    }.get(health_status(row), 5)


def rotation_recommendation(row: dict) -> str:
    return {
        "working": "use-first",
        "degraded": "late-retry",
        "quota-limited": "last-choice-quota",
        "permission-failed": "last-choice-permission",
        "model-not-accessible": "last-choice-model-access",
        "failed": "last-choice",
    }.get(health_status(row), "last-choice")


def _quota_remaining(row: dict) -> float:
    for key in (
        "rate_remaining_requests",
        "quota_remaining_day",
        "quota_remaining_minute",
        "rate_remaining_tokens",
    ):
        value = _to_number(row.get(key))
        if value is not None:
            return value
    return 0.0


def _to_number(value) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").strip()
    multipliers = {"K": 1_000, "M": 1_000_000}
    suffix = text[-1:].upper()
    if suffix in multipliers:
        text = text[:-1]
        multiplier = multipliers[suffix]
    else:
        multiplier = 1
    try:
        return float(text) * multiplier
    except ValueError:
        return None
