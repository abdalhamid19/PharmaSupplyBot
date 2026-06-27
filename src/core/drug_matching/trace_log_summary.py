"""Summary generation and output writing for trace log."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


_SUMMARY_COLS = [
    "code", "drug_name", "final_status", "final_match",
    "failure_stage", "primary_reason", "best_rejected_candidate",
    "ai_action", "ai_provider_model",
]


class SummaryWriter:
    """Handles summary generation and file output for trace logging."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def save_summary(self, path: Path):
        """Save summary CSV to the given path."""
        rows = self._summary_rows()
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=_SUMMARY_COLS)
            writer.writeheader()
            writer.writerows(rows)

    def _summary_rows(self):
        """Generate summary rows grouped by drug."""
        grouped: dict[tuple[str, str], list[dict]] = {}
        for row in self._parent._rows:
            if not row["drug_code"] and not row["drug_name"]:
                continue
            grouped.setdefault(
                (row["drug_code"], row["drug_name"]), [],
            ).append(row)
        return [self._summary_row(code, name, rows)
                for (code, name), rows in grouped.items()]

    def _summary_row(self, code, name, rows):
        """Generate a single summary row for one drug."""
        final = self._last(rows, "final")
        last_ai = self._last_ai_result(rows)
        ai_rows = [r for r in rows if r.get("ai_result")]
        rejected = [
            r for r in rows
            if r.get("decision") == "rejected" or r.get("reject_rule")
        ]
        if last_ai and self._ai_summary_status(last_ai) == "rejected":
            status = "no_match"
            final_match = "NONE"
        elif last_ai and self._ai_summary_status(last_ai) == "matched":
            status = "matched"
            final_match = last_ai.get("candidate_name", "") or self._last_candidate_name(rows)
        elif final:
            status = "matched" if final.get("final_match") != "NONE" else "no_match"
            final_match = final.get("final_match", "")
        else:
            status = "unknown"
            final_match = ""
        primary = (rejected[-1] if rejected else final) or rows[-1]
        failure_stage = primary.get("error_stage")
        if not failure_stage and status == "no_match":
            failure_stage = "matching"
        reason = (
            primary.get("error_code") or primary.get("reject_rule")
            or primary.get("selection_reason") or ""
        )
        best_rejected = rejected[-1].get("candidate_name", "") if rejected else ""
        return {
            "code": code,
            "drug_name": name,
            "final_status": status,
            "final_match": final_match,
            "failure_stage": failure_stage,
            "primary_reason": reason,
            "best_rejected_candidate": best_rejected,
            "ai_action": ai_rows[-1].get("ai_result", "") if ai_rows else "",
            "ai_provider_model": self._provider_model(rows),
        }

    @staticmethod
    def _last(rows, step):
        """Find the last row with the given step."""
        for row in reversed(rows):
            if row.get("step") == step:
                return row
        return None

    @staticmethod
    def _last_ai_result(rows):
        """Find the last AI result row."""
        for row in reversed(rows):
            if row.get("step") in {
                "ai_verify_result", "ai_search_result", "ai_review_result",
            }:
                return row
        return None

    @staticmethod
    def _ai_summary_status(row):
        """Determine AI summary status from result."""
        result = row.get("ai_result", "")
        if result in {"ai_rejected", "ai_review_rejected", "not_found"}:
            return "rejected"
        if result in {
            "ai_found", "ai_corrected", "ai_review_corrected",
            "ai_confirmed",
        }:
            return "matched"
        if result.endswith("_reviewed"):
            base = result.removesuffix("_reviewed")
            if base in {"ai_found", "ai_corrected", "ai_confirmed"}:
                return "matched"
        if result.endswith("_kept_low_confidence_review"):
            base = result.removesuffix("_kept_low_confidence_review")
            if base in {"ai_found", "ai_corrected", "ai_confirmed"}:
                return "matched"
            if base == "ai_rejected":
                return "rejected"
        return ""

    @staticmethod
    def _last_candidate_name(rows):
        """Find the last candidate name from rows."""
        for row in reversed(rows):
            candidate = row.get("candidate_name")
            if candidate:
                return candidate
            final_match = row.get("final_match")
            if final_match and final_match != "NONE":
                return final_match
        return ""

    @staticmethod
    def _provider_model(rows):
        """Extract provider/model string from rows."""
        for row in reversed(rows):
            provider = row.get("provider_used")
            model = row.get("model_used") or row.get("ai_model")
            if provider or model:
                return f"{provider}/{model}".strip("/")
        return ""


class TraceOutputWriter:
    """Handles CSV and TXT output writing for trace logs."""

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

    class _DefaultRow(dict):
        """Dict wrapper that returns '' for missing keys (used by TXT writer)."""

        _MISSING = ""

        def __missing__(self, key):
            return self._MISSING

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        """Save trace files (CSV, TXT, and summary)."""
        if not self._parent._enabled or not self._parent._rows:
            return "", "", ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self._parent._dir / f"{prefix}_{ts}.csv"
        txt_path = self._parent._dir / f"{prefix}_{ts}.txt"
        summary_path = self._parent._dir / f"{prefix}_summary_{ts}.csv"
        self._save_csv(csv_path)
        self._save_txt(txt_path)
        summary_writer = SummaryWriter(self._parent)
        summary_writer.save_summary(summary_path)
        import logging
        logger = logging.getLogger("pharmasupplybot.matching")
        logger.info(
            f"Trace saved: {csv_path} + {txt_path} + {summary_path}",
        )
        return str(csv_path), str(txt_path), str(summary_path)

    def _save_csv(self, path: Path):
        """Save trace data to CSV file."""
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=self._TRACE_CSV_COLS,
                restval="", extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(self._parent._rows)

    def _save_txt(self, path: Path):
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
        elif step == "fuzzy":
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
            ai = row["ai_phase"]
            ai_txt = f"  AI={ai}" if ai != "none" else ""
            f.write(
                f"  >> FINAL: match={row['final_match']}"
                f"  score={row['final_score']}"
                f"  method={row['final_method']}"
                f"{ai_txt}\n",
            )
            f.write(f"     reason: {row['selection_reason']}\n\n")
        elif step == "ai_verify_sent":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            f.write(
                f"  [AI VERIFY] sent to verify: "
                f"'{row['candidate_name']}'"
                f"  (brand={row['candidate_brand']})"
                f"  score={row['score']} < threshold={row['threshold']}"
                f"{model_txt}\n",
            )
        elif step == "ai_verify_result":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
            f.write(
                f"  [AI VERIFY] result={row['ai_result']}  "
                f"verifying='{row['candidate_name']}'  "
                f"confidence={row['score']}"
                f"{model_txt}{api_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
            if row.get('component_reason'):
                f.write(
                    f"     {row['component_reason']}\n",
                )
        elif step == "ai_search_sent":
            model_txt = f"  model={row['ai_model']}" if row.get('ai_model') else ""
            f.write(
                f"  [AI SEARCH] sent with {row['selection_reason']}{model_txt}\n"
            )
            if row.get('candidate_name'):
                f.write(
                    f"     candidates: {row['candidate_name']}\n"
                )
        elif step == "ai_search_result":
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
        elif step == "ai_review_sent":
            first_model_txt = f"  first_model={row['ai_model']}" if row.get('ai_model') else ""
            review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
            f.write(
                f"  [AI REVIEW] sent to second model: "
                f"first_decision={row['ai_result']}  "
                f"first_confidence={row['ai_confidence']}"
                f"{first_model_txt}{review_model_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
        elif step == "ai_review_result":
            review_model_txt = f"  review_model={row['ai_review_model']}" if row.get('ai_review_model') else ""
            api_txt = f"  API_FAILURES={row['api_failures']}" if row.get('api_failures') else ""
            f.write(
                f"  [AI REVIEW] result={row['ai_result']}  "
                f"review_confidence={row['ai_confidence']}"
                f"{review_model_txt}{api_txt}\n",
            )
            f.write(
                f"     {row['selection_reason']}\n",
            )
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
