"""Matching logic for MatchPipeline."""

import logging

from .normalizer import parse_drug

logger = logging.getLogger("pharmasupplybot.matching")


class MatchingEngine:
    """Handles algorithmic matching logic."""

    def __init__(self, cfg, index, trace=None):
        self._cfg = cfg
        self._index = index
        self._trace = trace

    def match_one(self, row, stats, row_index=""):
        """Match one drug, with trace if enabled."""
        drug_name = str(row.drug_name)
        price = getattr(row, "drug_price", None)
        if not self._trace or not self._trace.enabled:
            return self._index.best_match(drug_name, price)
        code = str(row.code)
        rec, score, method, trace = (
            self._index.best_match_detailed(drug_name, price)
        )
        parsed = parse_drug(drug_name)
        self._trace.log_normalization(
            code, drug_name, trace["norm"], trace["brand"],
            parsed.dosage_nums, parsed.form,
            row_index=row_index,
            components=self._trace.components_text(parsed),
        )
        for item in trace.get("candidates", []):
            self._trace.log_candidate_generated(
                code, drug_name, trace["norm"], trace["brand"],
                item["idx"], self._index, item["source"],
                item.get("rank", ""), item.get("score", ""),
                row_index=row_index,
            )
        for item in trace.get("score_breakdowns", []):
            self._trace.log_score_breakdown(
                code, drug_name, trace["norm"], trace["brand"],
                item, self._index, row_index=row_index,
            )
        self._trace.log_brand_lookup(
            code, drug_name, trace["norm"],
            trace["brand"], trace["brand_hits"],
            self._index, row_index=row_index,
        )
        for scorer_name, result in trace["fuzzy_steps"]:
            self._trace.log_fuzzy_step(
                code, drug_name, trace["norm"],
                trace["brand"], scorer_name, result,
                self._cfg.fuzzy_threshold, self._index,
                row_index=row_index,
            )
        for cidx, ok, reason in trace["component_checks"]:
            self._trace.log_component_check(
                code, drug_name, trace["norm"],
                trace["brand"], cidx, ok, reason,
                self._index, row_index=row_index,
            )
        match_name = rec["product_name_en"] if rec else None
        ai_eligible, ai_reason = self.ai_eligibility(
            rec, score, method, trace["norm"],
        )
        self._trace.log_final(
            code, drug_name, trace["norm"],
            trace["brand"], match_name, score, method,
            ai_eligible, ai_reason, row_index=row_index,
        )
        return rec, score, method

    def ai_eligibility(self, rec, score, method, norm):
        """Determine if this drug will go to AI and why."""
        if rec is None:
            if method in {"too_short", "invalid_name"}:
                return "none", f"{method} -> not eligible for AI"
            return "search", (
                "no_match -> eligible for AI search"
            )
        if score < self._cfg.ai_verify_threshold:
            return "verify", (
                f"score={round(score,1)} "
                f"< ai_threshold={self._cfg.ai_verify_threshold}"
                f" -> eligible for AI verify"
            )
        return "none", (
            f"score={round(score,1)} "
            f">= ai_threshold={self._cfg.ai_verify_threshold}"
            f" -> strong match, no AI needed"
        )

    def make_row(self, row, rec, score, method, stats):
        """Create a result row from matching data."""
        code = str(row.code)
        drug_name = str(row.drug_name)
        drug_price = getattr(row, "drug_price", "")
        if rec is not None:
            key = "brand_index" if "brand" in method else "fuzzy"
            stats[key] += 1
            return {
                "code": code, "drug_name": drug_name,
                "matched_product_name_en": rec["product_name_en"],
                "matched_product_name_ar": rec["product_name_ar"],
                "matched_store_product_id": rec["store_product_id"],
                "match_score": round(score, 1),
                "verified": "algo_match",
                "match_method": method,
                "ai_confidence": "",
                "ai_review_confidence": "",
                "_drug_price": drug_price,
                "_matched_price": rec.get("price", ""),
            }
        stats["no_match"] += 1
        return {
            "code": code, "drug_name": drug_name,
            "matched_product_name_en": "",
            "matched_product_name_ar": "",
            "matched_store_product_id": "",
            "match_score": "", "verified": "",
            "match_method": method,
            "ai_confidence": "",
            "ai_review_confidence": "",
            "_drug_price": drug_price,
            "_matched_price": "",
        }


__all__ = ["MatchingEngine"]
