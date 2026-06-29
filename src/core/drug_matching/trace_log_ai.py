"""AI verification, search, and review logging for trace log."""

from __future__ import annotations

from .trace_log_ai_mixins import (
    PreflightLoggingMethods,
    RotationLoggingMethods,
    APILoggingMethods,
)


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


class AIEventLogger:
    """Handles AI verification, search, and review events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger
        self._verify = AIVerifyLogger(parent_logger)
        self._search = AISearchLogger(parent_logger)
        self._review = AIReviewLogger(parent_logger)
        self._rotation = AIRotationLogger(parent_logger)

    # Verify methods
    def log_ai_verify_sent(self, *args, **kwargs):
        """Log when a match is sent to AI for verification."""
        return self._verify.log_ai_verify_sent(*args, **kwargs)

    def log_ai_verify_result(self, *args, **kwargs):
        """Log the result of AI verification."""
        return self._verify.log_ai_verify_result(*args, **kwargs)

    # Search methods
    def log_ai_search_sent(self, *args, **kwargs):
        """Log when a search is sent to AI."""
        return self._search.log_ai_search_sent(*args, **kwargs)

    def log_ai_search_result(self, *args, **kwargs):
        """Log the result of AI search."""
        return self._search.log_ai_search_result(*args, **kwargs)

    def log_ai_search_not_eligible(self, *args, **kwargs):
        """Log when AI search is not eligible for a drug."""
        return self._search.log_ai_search_not_eligible(*args, **kwargs)

    # Review methods
    def log_ai_review_sent(self, *args, **kwargs):
        """Log when a decision is sent to AI review."""
        return self._review.log_ai_review_sent(*args, **kwargs)

    def log_ai_review_result(self, *args, **kwargs):
        """Log the result of AI review."""
        return self._review.log_ai_review_result(*args, **kwargs)

    # Rotation methods
    def log_ai_skip(self, *args, **kwargs):
        """Log when an AI phase is skipped."""
        return self._rotation.log_ai_skip(*args, **kwargs)

    def log_ai_preflight_start(self, *args, **kwargs):
        """Log AI preflight check start."""
        return self._rotation.log_ai_preflight_start(*args, **kwargs)

    def log_ai_preflight_result(self, *args, **kwargs):
        """Log AI preflight check result."""
        return self._rotation.log_ai_preflight_result(*args, **kwargs)

    def log_rotation_preflight_start(self, *args, **kwargs):
        """Log rotation preflight check start."""
        return self._rotation.log_rotation_preflight_start(*args, **kwargs)

    def log_rotation_ranked_attempt(self, *args, **kwargs):
        """Log a ranked rotation attempt."""
        return self._rotation.log_rotation_ranked_attempt(*args, **kwargs)

    def log_api_attempts(self, *args, **kwargs):
        """Log API attempts with rotation tracking."""
        return self._rotation.log_api_attempts(*args, **kwargs)

    # Parse failure
    def log_ai_parse_failure(self, code, name, norm, brand, raw_excerpt,
        model_used="", row_index="",
    ):
        """Log AI parse failure."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="ai_parse",
            decision="parse_failed", decision_source="ai_client",
            error_stage="ai_parse", error_code="invalid_json",
            model_used=model_used, parse_failed="true",
        )
        row["step"] = "ai_parse_failure"
        row["ai_model"] = model_used
        row["selection_reason"] = raw_excerpt[:200]
        self._parent._rows.append(row)


__all__ = ["AIEventLogger"]
