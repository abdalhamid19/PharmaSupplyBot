"""Phase 2 & 3 AI steps for trace logging."""

from __future__ import annotations


class Phase2Methods:
    """Phase 2 & 3 AI logging methods for MatchTraceLog."""

    def log_ai_verify_sent(
        self, code, name, norm, brand, score, threshold,
        matched_name, matched_brand, method,
        ai_model="", price_context="", row_index="",
    ):
        """Log AI verification sent event."""
        self._ai_logger.log_ai_verify_sent(
            code, name, norm, brand, score, threshold,
            matched_name, matched_brand, method,
            ai_model, price_context, row_index,
        )

    def log_ai_verify_result(
        self, code, name, norm, brand,
        is_correct, ai_action, detail,
        matched_name, confidence, ai_reason,
        corrected_to,
        model_used="", api_failures="", row_index="",
        parse_failed=False,
    ):
        """Log AI verification result event."""
        self._ai_logger.log_ai_verify_result(
            code, name, norm, brand,
            is_correct, ai_action, detail,
            matched_name, confidence, ai_reason,
            corrected_to,
            model_used, api_failures, row_index,
            parse_failed,
        )

    def log_ai_search_sent(
        self, code, name, norm, brand,
        n_candidates, candidate_names,
        ai_model="", price_context="", row_index="",
    ):
        """Log AI search sent event."""
        self._ai_logger.log_ai_search_sent(
            code, name, norm, brand,
            n_candidates, candidate_names,
            ai_model, price_context, row_index,
        )

    def log_ai_search_result(
        self, code, name, norm, brand,
        found, match_name, confidence,
        model_used="", api_failures="", accept_threshold=0.75,
        row_index="", error_code="", parse_failed=False,
    ):
        """Log AI search result event."""
        self._ai_logger.log_ai_search_result(
            code, name, norm, brand,
            found, match_name, confidence,
            model_used, api_failures, accept_threshold,
            row_index, error_code, parse_failed,
        )

    def log_ai_review_sent(
        self, code, name, norm, brand,
        first_decision, first_confidence, matched_name,
        first_model="", review_model="", api_failed=False,
        price_context="", row_index="",
    ):
        """Log AI review sent event."""
        self._ai_logger.log_ai_review_sent(
            code, name, norm, brand,
            first_decision, first_confidence, matched_name,
            first_model, review_model, api_failed,
            price_context, row_index,
        )

    def log_ai_review_result(
        self, code, name, norm, brand,
        agree, review_confidence, review_reason, final_action,
        review_model="", api_failures="", row_index="",
        parse_failed=False,
    ):
        """Log AI review result event."""
        self._ai_logger.log_ai_review_result(
            code, name, norm, brand,
            agree, review_confidence, review_reason, final_action,
            review_model, api_failures, row_index,
            parse_failed,
        )

    def log_ai_skip(self, code, name, norm, brand, phase, reason, row_index=""):
        """Log AI skip event."""
        self._ai_logger.log_ai_skip(code, name, norm, brand, phase, reason, row_index)

    def log_ai_search_not_eligible(
        self, code, name, norm, brand, reason, row_index="",
    ):
        """Log AI search not eligible event."""
        self._ai_logger.log_ai_search_not_eligible(
            code, name, norm, brand, reason, row_index,
        )

    def log_ai_preflight_start(self, models, key_count):
        """Log AI preflight start event."""
        self._ai_logger.log_ai_preflight_start(models, key_count)

    def log_ai_preflight_result(self, rows, healthy_count):
        """Log AI preflight result event."""
        self._ai_logger.log_ai_preflight_result(rows, healthy_count)

    def log_rotation_preflight_start(self, attempts_count, detail=""):
        """Log rotation preflight start event."""
        self._ai_logger.log_rotation_preflight_start(attempts_count, detail)

    def log_rotation_ranked_attempt(self, row):
        """Log rotation ranked attempt event."""
        self._ai_logger.log_rotation_ranked_attempt(row)

    def log_api_attempts(self, code, name, norm, brand, attempts, row_index=""):
        """Log API attempts event."""
        self._ai_logger.log_api_attempts(code, name, norm, brand, attempts, row_index)

    def log_ai_parse_failure(
        self, code, name, norm, brand, raw_excerpt,
        model_used="", row_index="",
    ):
        """Log AI parse failure event."""
        self._ai_logger.log_ai_parse_failure(
            code, name, norm, brand, raw_excerpt,
            model_used, row_index,
        )
