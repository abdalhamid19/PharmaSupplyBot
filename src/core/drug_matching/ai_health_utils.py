"""Utility functions for AI health checks."""

import time
from datetime import datetime, timezone
from typing import Any


def split_csv(value: str) -> list[str]:
    """Split CSV value into list."""
    return [item.strip() for item in value.split(",") if item.strip()]


def dedupe(items: list[str]) -> list[str]:
    """Remove duplicates from list while preserving order."""
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def mask_key(key: str) -> str:
    """Mask API key for logging."""
    return f"...{key[-6:]}" if key else ""


def _clean_header(value: Any) -> str:
    """Clean header value."""
    return str(value).strip() if value not in (None, "") else ""


def _duration_from_seconds(seconds: float) -> str:
    """Convert seconds to human-readable duration."""
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
        seconds = number - now if number > 1_000_000_000 else number
        return _duration_from_seconds(seconds)
    try:
        reset_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        return _duration_from_seconds(reset_at.timestamp() - now)
    except ValueError:
        return raw


def _first_header(headers, names: list[str]) -> str:
    """Extract first available header from a list of possible names."""
    for name in names:
        value = headers.get(name)
        if value not in (None, ""):
            return _clean_header(value)
    return ""


__all__ = [
    "split_csv",
    "dedupe",
    "mask_key",
    "_clean_header",
    "_duration_from_seconds",
    "reset_in_text",
    "_first_header",
]
