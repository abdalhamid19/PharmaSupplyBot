"""AI rotation and preflight logging for trace log."""

from __future__ import annotations

from .trace_log_ai_rotation_preflight import PreflightLoggingMethods
from .trace_log_ai_rotation_rotation import RotationLoggingMethods
from .trace_log_ai_rotation_api import APILoggingMethods


class AIRotationLogger(PreflightLoggingMethods, RotationLoggingMethods, APILoggingMethods):
    """Handles AI rotation and preflight events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_ai_skip(self, code, name, norm, brand, phase, reason, row_index=""):
        """Log when an AI phase is skipped."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase=f"ai_{phase}",
            decision="skipped", decision_source=f"ai_{phase}",
            error_stage=f"ai_{phase}", error_code=reason,
        )
        row["step"] = "ai_skip"
        row["ai_phase"] = phase
        row["ai_result"] = "skipped"
        row["selection_reason"] = reason
        self._parent._rows.append(row)


__all__ = ["AIRotationLogger"]
