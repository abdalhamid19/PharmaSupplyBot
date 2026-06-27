"""CSV output writing for trace log."""

import csv
from pathlib import Path


class TraceCSVWriter:
    """Handles CSV output writing for trace logs."""

    _TRACE_CSV_COLS = [
        "run_id", "row_index", "phase", "decision", "decision_source",
        "error_stage", "error_code", "reject_rule",
        "inventory_components", "candidate_components",
        "base_score", "price_bonus", "final_candidate_score",
        "candidate_rank", "candidate_source",
        "threshold_name", "threshold_value",
        "api_attempt", "api_status", "model_used", "fallback_used",
        "parse_failed", "provider_used",
        "drug_code", "drug_name", "norm", "brand",
        "step", "candidate_name", "candidate_id",
        "candidate_brand", "candidate_norm",
        "score", "scorer", "threshold",
        "component_ok", "component_reason",
        "ai_phase", "ai_result", "ai_confidence",
        "ai_model", "ai_review_model", "api_failures",
        "selection_reason",
        "final_match", "final_score", "final_method",
    ]

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def save_csv(self, path: Path):
        """Save trace data to CSV file."""
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=self._TRACE_CSV_COLS,
                restval="", extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(self._parent._rows)


__all__ = ["TraceCSVWriter"]
