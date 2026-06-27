"""AI search logging for trace log."""


class AISearchLogger:
    """Handles AI search events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_ai_search_sent(
        self, code, name, norm, brand,
        n_candidates, candidate_names,
        ai_model="", price_context="", row_index="",
    ):
        """Log when a search is sent to AI."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="sent", decision_source="ai_search",
            candidate_source="ai_candidates",
        )
        row["step"] = "ai_search_sent"
        row["ai_phase"] = "search"
        row["candidate_name"] = "; ".join(candidate_names[:5])
        row["ai_model"] = ai_model
        row["selection_reason"] = (
            f"no_match + {n_candidates} candidates found"
            f" -> sent to AI model={ai_model} to pick best match"
        )
        if price_context:
            row["selection_reason"] += f" | price_context={price_context}"
        self._parent._rows.append(row)

    def log_ai_search_result(
        self, code, name, norm, brand,
        found, match_name, confidence,
        model_used="", api_failures="", accept_threshold=0.75,
        row_index="", error_code="", parse_failed=False,
    ):
        """Log the result of AI search."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="ai_found" if found else "not_found",
            decision_source="ai_search",
            error_stage="" if found else "ai_search",
            error_code=error_code if not found else "",
            threshold_name="ai_search_accept_confidence",
            threshold_value=accept_threshold,
            model_used=model_used,
            parse_failed=str(bool(parse_failed)).lower(),
        )
        row["step"] = "ai_search_result"
        row["ai_phase"] = "search"
        row["ai_result"] = "ai_found" if found else "not_found"
        row["ai_confidence"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["candidate_name"] = match_name or ""
        row["score"] = round(float(confidence), 2) if confidence not in (None, "") else ""
        row["ai_model"] = model_used
        row["api_failures"] = api_failures
        confidence_text = (
            round(float(confidence), 2)
            if confidence not in (None, "") else "N/A"
        )
        if found:
            threshold_text = f" >= {accept_threshold} -> accepted"
        elif confidence not in (None, "") and float(confidence) < float(accept_threshold):
            threshold_text = f" < {accept_threshold} -> rejected"
        elif error_code:
            threshold_text = f" error={error_code} -> rejected"
        else:
            threshold_text = f" >= {accept_threshold} but no accepted record -> rejected"
        row["selection_reason"] = (
            f"AI_model={model_used}"
            f" confidence={confidence_text}"
            f"{threshold_text}"
        )
        if api_failures:
            row["selection_reason"] += f" | API_failures: {api_failures}"
        self._parent._rows.append(row)

    def log_ai_search_not_eligible(
        self, code, name, norm, brand, reason, row_index="",
    ):
        """Log when AI search is not eligible for a drug."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_search",
            decision="skipped", decision_source="ai_search",
            error_stage="ai_search", error_code="not_eligible",
        )
        row["step"] = "ai_search_not_eligible"
        row["ai_phase"] = "search"
        row["ai_result"] = "skipped"
        row["selection_reason"] = reason
        self._parent._rows.append(row)


__all__ = ["AISearchLogger"]
