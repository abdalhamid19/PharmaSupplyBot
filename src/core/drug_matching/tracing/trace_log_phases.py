"""Local matching trace methods."""

from __future__ import annotations


class Phase1Methods:
    def log_normalization(self, code, name, norm, brand, dosage, form, row_index="", components=""):
        if self._enabled and self._level >= 3:
            self._append(code, name, norm, brand, row_index=row_index, phase="normalize", step="normalize", selection_reason=f"dosage={dosage} form={form}", inventory_components=components)

    def log_candidate_generated(self, code, name, norm, brand, candidate, index, source, rank="", score="", row_index=""):
        self._candidate_logger.log_candidate_generated(code, name, norm, brand, candidate, index, source, rank, score, row_index)

    def log_score_breakdown(self, code, name, norm, brand, item, index, row_index=""):
        self._scoring_logger.log_score_breakdown(code, name, norm, brand, item, index, row_index)

    def log_brand_lookup(self, code, name, norm, brand, hits, index, row_index=""):
        self._candidate_logger.log_brand_lookup(code, name, norm, brand, hits, index, row_index)

    def log_fuzzy_step(self, code, name, norm, brand, scorer_name, result, threshold, index, row_index=""):
        self._scoring_logger.log_fuzzy_step(code, name, norm, brand, scorer_name, result, threshold, index, row_index)

    def log_component_check(self, code, name, norm, brand, cidx, ok, reason, index, row_index=""):
        self._scoring_logger.log_component_check(code, name, norm, brand, cidx, ok, reason, index, row_index)

    def log_final(self, code, name, norm, brand, match, score, method, *_ignored, row_index=""):
        self._append(code, name, norm, brand, row_index=row_index, phase="final", step="final", decision="matched" if match else "no_match", decision_source=method, final_match=match or "NONE", final_score=round(score, 1) if score else "", final_method=method)
