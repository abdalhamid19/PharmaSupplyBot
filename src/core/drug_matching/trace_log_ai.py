"""AI verification, search, and review logging for trace log."""

from .trace_log_ai_verify import AIVerifyLogger
from .trace_log_ai_search import AISearchLogger
from .trace_log_ai_review import AIReviewLogger
from .trace_log_ai_rotation import AIRotationLogger


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
