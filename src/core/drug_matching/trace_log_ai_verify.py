"""AI verification logging for trace log."""


class AIVerifyLogger:
    """Handles AI verification events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_ai_verify_sent(
        self, code, name, norm, brand, score, threshold,
        matched_name, matched_brand, method,
        ai_model="", price_context="", row_index="",
    ):
        """Log when a match is sent to AI for verification."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_verify",
            decision="sent", decision_source="ai_verify",
            threshold_name="ai_verify_threshold",
            threshold_value=threshold,
        )
        row["step"] = "ai_verify_sent"
        row["ai_phase"] = "verify"
        row["score"] = round(score, 1)
        row["threshold"] = threshold
        row["candidate_name"] = matched_name or ""
        row["candidate_brand"] = matched_brand or ""
        row["scorer"] = method
        row["ai_model"] = ai_model
        row["selection_reason"] = (
            f"algo matched '{matched_name}' "
            f"(brand={matched_brand}) "
            f"score={round(score, 1)} < ai_threshold={threshold}"
            f" -> sent to AI model={ai_model} to verify correctness"
        )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._parent._rows.append(row)

    def log_ai_verify_result(
        self, code, name, norm, brand,
        is_correct, ai_action, detail,
        matched_name, confidence, ai_reason,
        corrected_to,
        model_used="", api_failures="", row_index="",
        parse_failed=False,
    ):
        """Log the result of AI verification."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_verify",
            decision=ai_action, decision_source="ai_verify",
            error_stage="" if is_correct else "ai_verify",
            error_code="" if is_correct else ai_action,
            model_used=model_used, parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_verify_result"
        row["ai_phase"] = "verify"
        row["ai_result"] = ai_action
        row["ai_confidence"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["candidate_name"] = matched_name or ""
        row["score"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["ai_model"] = model_used
        row["api_failures"] = api_failures
        row["selection_reason"] = (
            f"AI_says={'correct' if is_correct else 'incorrect'}"
            f" model={model_used}"
            f" confidence={round(float(confidence), 2) if confidence not in (None, '') else 'N/A'}"
            f" reason='{ai_reason}'"
            f" action={ai_action}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        if corrected_to:
            row["component_reason"] = f"corrected_to={corrected_to}"
        self._parent._rows.append(row)


__all__ = ["AIVerifyLogger"]
