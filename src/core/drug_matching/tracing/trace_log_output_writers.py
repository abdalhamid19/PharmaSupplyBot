"""CSV and text writers for deterministic matching traces."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


class TraceCSVWriter:
    _TRACE_CSV_COLS = [
        "run_id", "row_index", "phase", "decision", "decision_source",
        "error_stage", "error_code", "reject_rule", "inventory_components",
        "candidate_components", "base_score", "price_bonus", "final_candidate_score",
        "candidate_rank", "candidate_source", "threshold_name", "threshold_value",
        "drug_code", "drug_name", "norm", "brand", "step", "candidate_name",
        "candidate_id", "candidate_brand", "candidate_norm", "score", "scorer",
        "threshold", "component_ok", "component_reason", "selection_reason",
        "final_match", "final_score", "final_method",
    ]

    def __init__(self, parent_logger):
        self._parent = parent_logger

    def save_csv(self, path: Path):
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self._TRACE_CSV_COLS, restval="", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(self._parent._rows)


class TraceTXTWriter:
    def __init__(self, parent_logger):
        self._parent = parent_logger

    def save_txt(self, path: Path):
        with path.open("w", encoding="utf-8") as handle:
            handle.write("MediCompare Deterministic Matching Trace\n")
            handle.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
            for row in self._parent._rows:
                handle.write(f"[{row.get('step', '')}] {row.get('drug_name', '')}")
                if row.get("candidate_name"):
                    handle.write(f" -> {row['candidate_name']}")
                if row.get("selection_reason"):
                    handle.write(f" | {row['selection_reason']}")
                if row.get("final_match"):
                    handle.write(f" | final={row['final_match']}")
                handle.write("\n")


__all__ = ["TraceCSVWriter", "TraceTXTWriter"]
