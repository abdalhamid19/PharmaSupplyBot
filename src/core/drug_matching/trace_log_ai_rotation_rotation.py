"""Rotation logging methods for AI rotation."""

from __future__ import annotations


class RotationLoggingMethods:
    """Mix-in methods for AI rotation logging."""

    def log_rotation_preflight_start(self, attempts_count, detail=""):
        """Log rotation preflight check start."""
        reason = f"testing {attempts_count} provider/key/model attempts"
        if detail:
            reason = f"{reason}; {detail}"
        self._parent._append(
            "", "", "", "",
            step="rotation_preflight_start",
            phase="ai_rotation",
            decision="started",
            decision_source="ai_rotation",
            selection_reason=reason,
        )

    def log_rotation_ranked_attempt(self, row):
        """Log a ranked rotation attempt."""
        self._parent._append(
            "", "", "", "",
            step="rotation_ranked_attempt",
            phase="ai_rotation",
            decision="healthy" if row.get("ok") else "failed",
            decision_source="ai_rotation",
            provider_used=row.get("provider", ""),
            model_used=row.get("model", ""),
            candidate_rank=row.get("rotation_rank", ""),
            api_status=row.get("http_status", ""),
            error_stage="" if row.get("ok") else "ai_rotation",
            error_code="" if row.get("ok") else row.get("error_type", ""),
            selection_reason=(
                f"rank={row.get('rotation_rank')} "
                f"provider={row.get('provider')} "
                f"model={row.get('model')} "
                f"key=...{row.get('key_suffix', '')} "
                f"score={row.get('rotation_score')} "
                f"reset={row.get('quota_reset_in') or row.get('retry_after_in') or 'n/a'}"
            ),
        )


__all__ = ["RotationLoggingMethods"]
