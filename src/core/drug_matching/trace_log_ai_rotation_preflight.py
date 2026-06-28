"""Preflight logging methods for AI rotation."""

from __future__ import annotations


class PreflightLoggingMethods:
    """Mix-in methods for AI preflight logging."""

    def log_ai_preflight_start(self, models, key_count):
        """Log AI preflight check start."""
        self._parent._append(
            "", "", "", "",
            step="ai_preflight_start",
            phase="ai_preflight",
            decision="started",
            decision_source="ai_health",
            selection_reason=(
                f"testing {key_count} key(s) x {len(models)} model(s): "
                f"{', '.join(models)}"
            ),
        )

    def log_ai_preflight_result(self, rows, healthy_count):
        """Log AI preflight check result."""
        status = "healthy" if healthy_count else "no_healthy_model"
        self._parent._append(
            "", "", "", "",
            step="ai_preflight_result",
            phase="ai_preflight",
            decision=status,
            decision_source="ai_health",
            error_stage="" if healthy_count else "ai_preflight",
            error_code="" if healthy_count else "no_healthy_model",
            selection_reason=(
                f"healthy_combos={healthy_count}; "
                f"tested={len(rows)}; "
                f"failures={self._preflight_failures(rows)}"
            ),
        )

    @staticmethod
    def _preflight_failures(rows):
        """Count failures by error type from preflight results."""
        counts = {}
        for row in rows:
            if row.get("ok"):
                continue
            key = row.get("error_type") or "unknown"
            counts[key] = counts.get(key, 0) + 1
        return "; ".join(f"{k}:{v}" for k, v in sorted(counts.items()))


__all__ = ["PreflightLoggingMethods"]
