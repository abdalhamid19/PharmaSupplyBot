"""Health checks and ranking for rotated AI attempts."""
from __future__ import annotations

from .ai_rotation import AIModelAttempt
from .ai_rotation_health_execution import run_rotation_health
from .ai_rotation_health_selection import (
    select_preflight_attempts,
    attempts_from_partial_health,
    cached_working_attempts,
    attempts_from_health,
)
from .ai_rotation_health_reports import write_rotation_reports, load_latest_rotation_health
from .ai_rotation_health_scoring import rank_health_rows
from .ai_rotation_health_status import health_status, _PERMANENT_FAILURES


__all__ = [
    "run_rotation_health",
    "select_preflight_attempts",
    "attempts_from_partial_health",
    "rank_health_rows",
    "write_rotation_reports",
    "load_latest_rotation_health",
    "cached_working_attempts",
    "attempts_from_health",
    "health_status",
    "_PERMANENT_FAILURES",
]
