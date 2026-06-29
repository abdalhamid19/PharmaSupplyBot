"""Output writing for trace log (CSV and TXT)."""

import csv
import logging
from datetime import datetime
from pathlib import Path

from .trace_log_summary import SummaryWriter


class StepWriters:
    """Helper class for writing different step types to TXT."""

    @staticmethod
    def write_brand_lookup(f, row):
        """Write brand lookup step."""
        if row["ai_result"] == "no_hits":
            f.write(
                f"  [brand_lookup] no hits  "
                f"({row['selection_reason']})\n",
            )
        else:
            f.write(
                f"  [brand_lookup] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  score={row['score']}\n",
            )

    @staticmethod
    def write_fuzzy(f, row):
        """Write fuzzy search step."""
        if "no candidate" in row.get("selection_reason", ""):
            f.write(
                f"  [fuzzy/{row['scorer']}] "
                f"no hit above threshold={row['threshold']}\n",
            )
        else:
            f.write(
                f"  [fuzzy/{row['scorer']}] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  score={row['score']}"
                f"  (threshold={row['threshold']})\n",
            )

    @staticmethod
    def write_final(f, row):
        """Write final match step."""
        ai = row["ai_phase"]
        ai_txt = f"  AI={ai}" if ai != "none" else ""
        f.write(
            f"  >> FINAL: match={row['final_match']}"
            f"  score={row['final_score']}"
            f"  method={row['final_method']}"
            f"{ai_txt}\n",
        )
        f.write(f"     reason: {row['selection_reason']}\n\n")

    @staticmethod
    def write_ai_verify_sent(f, row):
        """Write AI verify sent step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        f.write(
            f"  [AI VERIFY] sent to verify: "
            f"'{row['candidate_name']}'"
            f"  (brand={row['candidate_brand']})"
            f"  score={row['score']} < threshold={row['threshold']}"
            f"{model_txt}\n",
        )

    @staticmethod
    def write_ai_verify_result(f, row):
        """Write AI verify result step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        f.write(
            f"  [AI VERIFY] result={row['ai_result']}  "
            f"verifying='{row['candidate_name']}'  "
            f"confidence={row['score']}"
            f"{model_txt}{api_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")
        if row.get('component_reason'):
            f.write(f"     {row['component_reason']}\n")

    @staticmethod
    def write_ai_search_sent(f, row):
        """Write AI search sent step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        f.write(
            f"  [AI SEARCH] sent with {row['selection_reason']}{model_txt}\n"
        )
        if row.get('candidate_name'):
            f.write(f"     candidates: {row['candidate_name']}\n")

    @staticmethod
    def write_ai_search_result(f, row):
        """Write AI search result step."""
        model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        if row["ai_result"] == "ai_found":
            f.write(
                f"  [AI SEARCH] FOUND: "
                f"{row['candidate_name']}"
                f"  confidence={row['score']}"
                f"{model_txt}{api_txt}\n",
            )
        else:
            f.write(
                f"  [AI SEARCH] not found  "
                f"{row['selection_reason']}{api_txt}\n",
            )

    @staticmethod
    def write_ai_review_sent(f, row):
        """Write AI review sent step."""
        first_model_txt = f"  first_model={row['ai_model']}" if row.get('ai_model') else ""
        review_model_txt = (
            f"  review_model={row['ai_review_model']}"
            if row.get('ai_review_model') else ""
        )
        f.write(
            f"  [AI REVIEW] sent to second model: "
            f"first_decision={row['ai_result']}  "
            f"first_confidence={row['ai_confidence']}"
            f"{first_model_txt}{review_model_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")

    @staticmethod
    def write_ai_review_result(f, row):
        """Write AI review result step."""
        review_model_txt = (
            f"  review_model={row['ai_review_model']}"
            if row.get('ai_review_model') else ""
        )
        api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
        f.write(
            f"  [AI REVIEW] result={row['ai_result']}  "
            f"review_confidence={row['ai_confidence']}"
            f"{review_model_txt}{api_txt}\n",
        )
        f.write(f"     {row['selection_reason']}\n")


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


class TraceTXTWriter:
    """Handles TXT output writing for trace logs."""

    class _DefaultRow(dict):
        """Dict wrapper that returns '' for missing keys (used by TXT writer)."""

        _MISSING = ""

        def __missing__(self, key):
            return self._MISSING

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger
        self._step_writers = StepWriters()

    def save_txt(self, path: Path):
        """Save trace data to human-readable TXT file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("MediCompare Algorithm Trace Log\n")
            f.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Total steps: {len(self._parent._rows)}\n")
            f.write("=" * 80 + "\n\n")
            current_drug = None
            for raw_row in self._parent._rows:
                row = self._DefaultRow(raw_row)
                key = (row["drug_code"], row["drug_name"])
                if key != current_drug:
                    current_drug = key
                    f.write("-" * 60 + "\n")
                    f.write(
                        f"DRUG: [{row['drug_code']}] "
                        f"{row['drug_name']}\n",
                    )
                    f.write(
                        f"  norm={row['norm']}  "
                        f"brand={row['brand']}\n",
                    )
                self._write_step(f, row)
            f.write("=" * 80 + "\n")

    def _write_step(self, f, row):
        """Write a single step to the TXT output."""
        step = row["step"]
        if step == "normalize":
            f.write(f"  [normalize] {row['selection_reason']}\n")
        elif step == "brand_lookup":
            self._step_writers.write_brand_lookup(f, row)
        elif step == "fuzzy":
            self._step_writers.write_fuzzy(f, row)
        elif step == "component_check":
            self._write_component_check(f, row)
        elif step == "candidate_generated":
            self._write_candidate_generated(f, row)
        elif step == "score_breakdown":
            self._write_score_breakdown(f, row)
        elif step == "final":
            self._step_writers.write_final(f, row)
        elif step == "ai_verify_sent":
            self._step_writers.write_ai_verify_sent(f, row)
        elif step == "ai_verify_result":
            self._step_writers.write_ai_verify_result(f, row)
        elif step == "ai_search_sent":
            self._step_writers.write_ai_search_sent(f, row)
        elif step == "ai_search_result":
            self._step_writers.write_ai_search_result(f, row)
        elif step == "ai_review_sent":
            self._step_writers.write_ai_review_sent(f, row)
        elif step == "ai_review_result":
            self._step_writers.write_ai_review_result(f, row)
        elif step == "ai_skip":
            self._write_ai_skip(f, row)
        elif step == "ai_search_not_eligible":
            self._write_ai_search_not_eligible(f, row)
        elif step in {"rotation_preflight_start", "rotation_ranked_attempt"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"rotation_attempt_used", "rotation_attempt_disabled"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"ai_preflight_start", "ai_preflight_result"}:
            f.write(f"  [AI PREFLIGHT] {row['selection_reason']}\n")
        elif step == "api_attempt":
            self._write_api_attempt(f, row)
        elif step == "ai_parse_failure":
            self._write_ai_parse_failure(f, row)

    def _write_component_check(self, f, row):
        """Write component check step."""
        f.write(
            f"  [component_check] "
            f"{row['candidate_name']}"
            f"  brand={row['candidate_brand']}"
            f"  ok={row['component_ok']}"
            f"  reason={row['component_reason']}"
            f"  reject_rule={row.get('reject_rule', '')}\n",
        )

    def _write_candidate_generated(self, f, row):
        """Write candidate generated step."""
        f.write(
            f"  [candidate/{row['candidate_source']}] "
            f"rank={row['candidate_rank']} "
            f"{row['candidate_name']} score={row['score']}\n",
        )

    def _write_score_breakdown(self, f, row):
        """Write score breakdown step."""
        f.write(
            f"  [score/{row['candidate_source']}] "
            f"{row['candidate_name']} base={row['base_score']} "
            f"price_bonus={row['price_bonus']} "
            f"final={row['final_candidate_score']}\n",
        )

    def _write_ai_skip(self, f, row):
        """Write AI skip step."""
        f.write(
            f"  [AI {row['ai_phase'].upper()}] "
            f"SKIPPED: {row['selection_reason']}\n",
        )

    def _write_ai_search_not_eligible(self, f, row):
        """Write AI search not eligible step."""
        f.write(
            f"  [AI SEARCH] NOT ELIGIBLE: "
            f"{row['selection_reason']}\n",
        )

    def _write_api_attempt(self, f, row):
        """Write API attempt step."""
        f.write(
            f"  [API] model={row['model_used']} "
            f"status={row['api_status']} "
            f"fallback={row['fallback_used']} "
            f"parse_failed={row['parse_failed']} "
            f"{row['selection_reason']}\n",
        )

    def _write_ai_parse_failure(self, f, row):
        """Write AI parse failure step."""
        f.write(
            f"  [AI PARSE] model={row['model_used']} "
            f"invalid_json excerpt={row['selection_reason']}\n",
        )


class TraceOutputWriter:
    """Handles CSV and TXT output writing for trace logs."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger
        self._csv_writer = TraceCSVWriter(parent_logger)
        self._txt_writer = TraceTXTWriter(parent_logger)

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        """Save trace files (CSV, TXT, and summary)."""
        if not self._parent._enabled or not self._parent._rows:
            return "", "", ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self._parent._dir / f"{prefix}_{ts}.csv"
        txt_path = self._parent._dir / f"{prefix}_{ts}.txt"
        summary_path = self._parent._dir / f"{prefix}_summary_{ts}.csv"
        self._csv_writer.save_csv(csv_path)
        self._txt_writer.save_txt(txt_path)
        summary_writer = SummaryWriter(self._parent)
        summary_writer.save_summary(summary_path)
        logger = logging.getLogger("pharmasupplybot.matching")
        logger.info(
            f"Trace saved: {csv_path} + {txt_path} + {summary_path}",
        )
        return str(csv_path), str(txt_path), str(summary_path)


__all__ = [
    "StepWriters",
    "TraceCSVWriter",
    "TraceTXTWriter",
    "TraceOutputWriter",
]
