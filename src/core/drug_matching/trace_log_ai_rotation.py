"""AI rotation and preflight logging for trace log."""


class AIRotationLogger:
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

    def log_api_attempts(self, code, name, norm, brand, attempts, row_index=""):
        """Log API attempts with rotation tracking."""
        if not self._parent._enabled:
            return
        for item in attempts or []:
            row = self._parent._base(
                code, name, norm, brand,
                row_index=row_index, phase="api",
                decision=item.get("decision", ""),
                decision_source="api_client",
                error_stage=item.get("error_stage", ""),
                error_code=item.get("error_code", ""),
                api_attempt=item.get("attempt", ""),
                api_status=item.get("status", ""),
                model_used=item.get("model", ""),
                provider_used=item.get("provider", ""),
                fallback_used=str(bool(item.get("fallback_used"))).lower(),
                parse_failed=str(bool(item.get("parse_failed"))).lower(),
            )
            row["step"] = "api_attempt"
            row["ai_phase"] = item.get("phase", "")
            row["ai_model"] = item.get("model", "")
            suffix = item.get("key_suffix", "")
            key_txt = f" key=...{suffix}" if suffix else ""
            row["selection_reason"] = f"{item.get('reason', '')}{key_txt}"
            self._parent._rows.append(row)
            self._append_rotation_attempt_event(code, name, norm, brand, item, row_index)

    def _append_rotation_attempt_event(
        self, code, name, norm, brand, item, row_index="",
    ):
        """Append rotation attempt event if applicable."""
        provider = item.get("provider", "")
        if not provider:
            return
        decision = item.get("decision", "")
        if decision == "success":
            step = "rotation_attempt_used"
        elif decision == "disabled":
            step = "rotation_attempt_disabled"
        else:
            return
        self._parent._append(
            code, name, norm, brand,
            row_index=row_index, phase="ai_rotation",
            step=step, decision=decision,
            decision_source="ai_rotation",
            provider_used=provider,
            model_used=item.get("model", ""),
            api_status=item.get("status", ""),
            error_stage=item.get("error_stage", ""),
            error_code=item.get("error_code", ""),
            selection_reason=(
                f"{step}: provider={provider} "
                f"model={item.get('model', '')} "
                f"key=...{item.get('key_suffix', '')} "
                f"reason={item.get('reason', '')}"
            ),
        )


__all__ = ["AIRotationLogger"]
