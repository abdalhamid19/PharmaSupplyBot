"""TXT output writing for trace log."""

from datetime import datetime
from pathlib import Path

from .trace_log_output_txt_steps import StepWriters


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
            f.write(
                f"  [component_check] "
                f"{row['candidate_name']}"
                f"  brand={row['candidate_brand']}"
                f"  ok={row['component_ok']}"
                f"  reason={row['component_reason']}"
                f"  reject_rule={row.get('reject_rule', '')}\n",
            )
        elif step == "candidate_generated":
            f.write(
                f"  [candidate/{row['candidate_source']}] "
                f"rank={row['candidate_rank']} "
                f"{row['candidate_name']} score={row['score']}\n",
            )
        elif step == "score_breakdown":
            f.write(
                f"  [score/{row['candidate_source']}] "
                f"{row['candidate_name']} base={row['base_score']} "
                f"price_bonus={row['price_bonus']} "
                f"final={row['final_candidate_score']}\n",
            )
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
            f.write(
                f"  [AI {row['ai_phase'].upper()}] "
                f"SKIPPED: {row['selection_reason']}\n",
            )
        elif step == "ai_search_not_eligible":
            f.write(
                f"  [AI SEARCH] NOT ELIGIBLE: "
                f"{row['selection_reason']}\n",
            )
        elif step in {"rotation_preflight_start", "rotation_ranked_attempt"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"rotation_attempt_used", "rotation_attempt_disabled"}:
            f.write(f"  [AI ROTATION] {row['selection_reason']}\n")
        elif step in {"ai_preflight_start", "ai_preflight_result"}:
            f.write(f"  [AI PREFLIGHT] {row['selection_reason']}\n")
        elif step == "api_attempt":
            f.write(
                f"  [API] model={row['model_used']} "
                f"status={row['api_status']} "
                f"fallback={row['fallback_used']} "
                f"parse_failed={row['parse_failed']} "
                f"{row['selection_reason']}\n",
            )
        elif step == "ai_parse_failure":
            f.write(
                f"  [AI PARSE] model={row['model_used']} "
                f"invalid_json excerpt={row['selection_reason']}\n",
            )


__all__ = ["TraceTXTWriter"]
