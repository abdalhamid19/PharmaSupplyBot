"""API attempts logging methods for AI rotation."""

from __future__ import annotations


class APILoggingMethods:
    """Mix-in methods for API attempts logging."""

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


__all__ = ["APILoggingMethods"]
