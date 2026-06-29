"""AI review logging for trace log."""


class AIReviewLogger:
    """Handles AI review events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_ai_review_sent(
        self, code, name, norm, brand,
        first_decision, first_confidence, matched_name,
        first_model="", review_model="", api_failed=False,
        price_context="", row_index="",
    ):
        """Log when a decision is sent to AI review."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_review",
            decision="sent", decision_source="ai_review",
            model_used=first_model,
        )
        row["step"] = "ai_review_sent"
        row["ai_phase"] = "review"
        row["ai_result"] = first_decision
        row["ai_confidence"] = (
            round(float(first_confidence), 2) if first_confidence not in (None, "") else ""
        )
        row["candidate_name"] = matched_name or ""
        row["ai_model"] = first_model
        row["ai_review_model"] = review_model
        if api_failed:
            row["selection_reason"] = (
                f"first_AI=UNAVAILABLE (API failed)"
                f" -> sent to review model={review_model} for FRESH verification"
            )
        else:
            conf_str = (
                round(float(first_confidence), 2)
                if first_confidence not in (None, "")
                else "N/A"
            )
            row["selection_reason"] = (
                f"first_AI={first_decision} model={first_model}"
                f" confidence={conf_str}"
                f" < review_threshold -> sent to review model={review_model}"
            )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._parent._rows.append(row)

    def log_ai_review_result(
        self, code, name, norm, brand,
        agree, review_confidence, review_reason, final_action,
        review_model="", api_failures="", row_index="",
        parse_failed=False,
    ):
        """Log the result of AI review."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_review",
            decision=final_action, decision_source="ai_review",
            error_stage="" if agree else "ai_review",
            error_code="" if agree else final_action,
            model_used=review_model,
            parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_review_result"
        row["ai_phase"] = "review"
        row["ai_result"] = final_action
        row["ai_confidence"] = (
            round(float(review_confidence), 2) if review_confidence not in (None, "") else ""
        )
        row["ai_review_model"] = review_model
        row["api_failures"] = api_failures
        conf_str = (
            round(float(review_confidence), 2)
            if review_confidence not in (None, "")
            else "N/A"
        )
        row["selection_reason"] = (
            f"second_AI={'agrees' if agree else 'disagrees'}"
            f" model={review_model}"
            f" confidence={conf_str}"
            f" reason='{review_reason}'"
            f" action={final_action}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        self._parent._rows.append(row)


__all__ = ["AIReviewLogger"]
