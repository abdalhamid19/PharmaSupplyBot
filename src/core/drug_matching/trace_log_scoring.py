"""Scoring and fuzzy matching logging for trace log."""

from __future__ import annotations


class ScoringEventLogger:
    """Handles scoring breakdown and fuzzy step events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_score_breakdown(
        self, code, name, norm, brand, item, index, row_index="",
    ):
        """Log detailed score breakdown for a candidate."""
        if not self._parent._enabled:
            return
        idx = item["idx"]
        rec = index.get_record(idx)
        parsed = index.get_parsed(idx)
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="scoring",
            decision="score_calculated",
            decision_source=item.get("source", ""),
            candidate_source=item.get("source", ""),
            candidate_rank=item.get("rank", ""),
            base_score=round(item.get("base_score", 0), 1),
            price_bonus=round(item.get("price_bonus", 0), 1),
            final_candidate_score=round(item.get("final_score", 0), 1),
            threshold_name="fuzzy_threshold",
            threshold_value=item.get("threshold", ""),
            candidate_components=self._parent.components_text(parsed),
        )
        row["step"] = "score_breakdown"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(idx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["score"] = round(item.get("final_score", 0), 1)
        row["selection_reason"] = (
            f"base={row['base_score']} + price_bonus={row['price_bonus']} "
            f"=> final={row['final_candidate_score']}"
        )
        self._parent._rows.append(row)

    def log_fuzzy_step(
        self, code, name, norm, brand,
        scorer_name, result, threshold, index,
        row_index="",
    ):
        """Log a fuzzy matching step."""
        if not self._parent._enabled:
            return
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="candidate_generation",
            decision_source=f"fuzzy:{scorer_name}",
            threshold_name="fuzzy_threshold",
            threshold_value=threshold,
        )
        row["step"] = "fuzzy"
        row["scorer"] = scorer_name
        row["threshold"] = threshold
        if result:
            match_name, score, idx = result
            rec = index.get_record(idx)
            parsed = index.get_parsed(idx)
            row["candidate_name"] = match_name
            row["candidate_id"] = str(idx)
            row["candidate_brand"] = parsed.brand
            row["candidate_norm"] = parsed.normalized
            row["candidate_components"] = self._parent.components_text(parsed)
            row["candidate_source"] = f"fuzzy:{scorer_name}"
            row["decision"] = "generated"
            row["score"] = round(score, 1)
            row["selection_reason"] = (
                f"score={round(score, 1)} >= threshold={threshold}"
            )
        else:
            row["decision"] = "no_candidates"
            row["error_stage"] = "candidate_generation"
            row["error_code"] = "below_threshold"
            row["selection_reason"] = (
                f"no candidate above threshold={threshold}"
            )
        self._parent._rows.append(row)

    def log_component_check(
        self, code, name, norm, brand,
        cidx, ok, reason, index,
        row_index="",
    ):
        """Log component validation check for a candidate."""
        if not self._parent._enabled or self._parent._level < self._parent.TRACE_NORMAL:
            return
        rec = index.get_record(cidx)
        parsed = index.get_parsed(cidx)
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="component_check",
            decision="accepted" if ok else "rejected",
            decision_source="components_match",
            reject_rule="" if ok else reason,
            error_stage="" if ok else "component_check",
            error_code="" if ok else reason,
            candidate_components=self._parent.components_text(parsed),
        )
        row["step"] = "component_check"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(cidx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["component_ok"] = "yes" if ok else "no"
        row["component_reason"] = reason
        row["selection_reason"] = (
            f"components_match={'ok' if ok else 'FAIL'}"
            f" reason={reason}"
        )
        self._parent._rows.append(row)
