"""Candidate generation logging for trace log."""

from __future__ import annotations


class CandidateEventLogger:
    """Handles candidate generation and brand lookup events for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def log_candidate_generated(
        self, code, name, norm, brand, candidate, index,
        source, rank="", score="", row_index="",
    ):
        """Log a candidate generated during matching."""
        if not self._parent._enabled or self._parent._level < self._parent.TRACE_VERBOSE or candidate is None:
            return
        idx = candidate[0] if isinstance(candidate, tuple) else candidate
        rec = index.get_record(idx)
        parsed = index.get_parsed(idx)
        row = self._parent._base(
            code, name, norm, brand,
            row_index=row_index, phase="candidate_generation",
            decision="generated", decision_source=source,
            candidate_source=source, candidate_rank=rank,
            candidate_components=self._parent.components_text(parsed),
        )
        row["step"] = "candidate_generated"
        row["candidate_name"] = rec["product_name_en"]
        row["candidate_id"] = str(idx)
        row["candidate_brand"] = parsed.brand
        row["candidate_norm"] = parsed.normalized
        row["score"] = round(score, 1) if score not in (None, "") else ""
        row["selection_reason"] = f"{source} candidate rank={rank}"
        self._parent._rows.append(row)

    def log_brand_lookup(
        self, code, name, norm, brand, hits, index, row_index="",
    ):
        """Log brand index lookup results."""
        if not self._parent._enabled:
            return
        if not hits:
            row = self._parent._base(
                code, name, norm, brand,
                row_index=row_index, phase="candidate_generation",
                decision="no_candidates", decision_source="brand_index",
                error_stage="candidate_generation", error_code="no_brand_hits",
            )
            row["step"] = "brand_lookup"
            row["selection_reason"] = (
                f"brand={brand} len={len(brand)} (need >=3)"
            )
            row["ai_result"] = "no_hits"
            self._parent._rows.append(row)
            return
        for rank, (idx, score) in enumerate(hits, start=1):
            rec = index.get_record(idx)
            parsed = index.get_parsed(idx)
            row = self._parent._base(
                code, name, norm, brand,
                row_index=row_index, phase="candidate_generation",
                decision="generated", decision_source="brand_index",
                candidate_source="brand_index", candidate_rank=rank,
                candidate_components=self._parent.components_text(parsed),
            )
            row["step"] = "brand_lookup"
            row["candidate_name"] = rec["product_name_en"]
            row["candidate_id"] = str(idx)
            row["candidate_brand"] = parsed.brand
            row["candidate_norm"] = parsed.normalized
            row["score"] = round(score, 1)
            row["scorer"] = "token_sort_ratio"
            row["selection_reason"] = (
                f"brand_prefix_match score={round(score, 1)}"
            )
            self._parent._rows.append(row)
