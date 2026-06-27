"""Summary generation for trace log."""

import csv
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


__all__ = ["SummaryWriter"]
