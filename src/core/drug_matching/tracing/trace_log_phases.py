"""Phase 1, 2 & 3 algorithmic and AI steps for trace logging."""

from __future__ import annotations


class Phase1Methods:
    """Phase 1 algorithmic logging methods for MatchTraceLog."""

    def log_normalization(
        self, code, name, norm, brand, dosage, form,
        row_index="", components="",
    ):
        """Log drug normalization step."""
        if not self._enabled or self._level < 3:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="normalize",
            decision="parsed", decision_source="normalizer",
            inventory_components=components,
        )
        row["step"] = "normalize"
        row["selection_reason"] = (
            f"dosage={dosage} form={form}"
        )
        self._rows.append(row)

    def log_candidate_generated(
        self, code, name, norm, brand, candidate, index,
        source, rank="", score="", row_index="",
    ):
        """Log candidate generation event."""
        self._candidate_logger.log_candidate_generated(
            code, name, norm, brand, candidate, index,
            source, rank, score, row_index,
        )

    def log_score_breakdown(
        self, code, name, norm, brand, item, index, row_index="",
    ):
        """Log score breakdown event."""
        self._scoring_logger.log_score_breakdown(
            code, name, norm, brand, item, index, row_index,
        )

    def log_brand_lookup(
        self, code, name, norm, brand, hits, index, row_index="",
    ):
        """Log brand lookup event."""
        self._candidate_logger.log_brand_lookup(
            code, name, norm, brand, hits, index, row_index,
        )

    def log_fuzzy_step(
        self, code, name, norm, brand,
        scorer_name, result, threshold, index,
        row_index="",
    ):
        """Log fuzzy matching step."""
        self._scoring_logger.log_fuzzy_step(
            code, name, norm, brand,
            scorer_name, result, threshold, index,
            row_index,
        )

    def log_component_check(
        self, code, name, norm, brand,
        cidx, ok, reason, index,
        row_index="",
    ):
        """Log component check event."""
        self._scoring_logger.log_component_check(
            code, name, norm, brand,
            cidx, ok, reason, index,
            row_index,
        )

    def log_final(
        self, code, name, norm, brand,
        match, score, method, ai_eligible, ai_reason,
        row_index="",
    ):
        """Log final match decision."""
        if not self._enabled:
            return
        row = self._base(
            code, name, norm, brand,
            row_index=row_index, phase="final",
            decision="matched" if match else "no_match",
            decision_source=method,
            error_stage="" if match else "matching",
            error_code="" if match else method,
            threshold_name="ai_verify_threshold",
        )
        row["step"] = "final"
        row["final_match"] = match or "NONE"
        row["final_score"] = round(score, 1) if score else ""
        row["final_method"] = method
        if ai_eligible == "verify":
            row["ai_phase"] = "verify"
        elif ai_eligible == "search":
            row["ai_phase"] = "search"
        else:
            row["ai_phase"] = "none"
        row["ai_result"] = ai_eligible
        row["selection_reason"] = ai_reason
        self._rows.append(row)


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
