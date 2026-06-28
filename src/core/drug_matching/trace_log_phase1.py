"""Phase 1 algorithmic steps for trace logging."""

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
        row["selection_reason"] = f"dosage={dosage} form={form}"
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
        row["ai_phase"] = (
            "verify" if ai_eligible == "verify"
            else "search" if ai_eligible == "search"
            else "none"
        )
        row["ai_result"] = ai_eligible
        row["selection_reason"] = ai_reason
        self._rows.append(row)
