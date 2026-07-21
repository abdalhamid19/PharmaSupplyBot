"""Pipeline I/O operations for data loading, saving, and progress tracking."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from ..config import MatchingConfig

logger = logging.getLogger(__name__)


def _manual_review_path(output_path: str) -> str:
    """Return a manual-review path next to the main output CSV."""
    path = Path(output_path)
    return str(path.with_name(f"{path.stem}_manual_review{path.suffix}"))


def _manual_review_reason_column(row: pd.Series) -> str:
    """Build a human-readable reason explaining why this row needs review."""
    parts = _manual_review_base_reasons(row)
    _append_component_review_reason(parts, row)
    return "; ".join(parts) if parts else "needs_review"


def _manual_review_base_reasons(row: pd.Series) -> list[str]:
    """Extract base reasons for manual review."""
    verified = str(row.get("verified", "") or "")
    has_match = bool(row.get("matched_product_name_en"))
    if not has_match:
        return ["no_match_found"]
    if verified == "ai_rejected":
        return ["ai_rejected_match"]
    if verified == "ai_review_rejected":
        return ["ai_review_rejected_match"]
    if verified in ("ai_confirmed", "ai_corrected", "ai_found"):
        return ["low_confidence_ai_match"]
    return _score_review_reasons(row)


def _score_review_reasons(row: pd.Series) -> list[str]:
    """Extract score-based review reasons."""
    score = pd.to_numeric(row.get("match_score", 0), errors="coerce")
    if pd.notna(score) and score < 90:
        return [f"uncertain_score({score:.0f})"]
    return []


def _append_component_review_reason(parts: list[str], row: pd.Series) -> None:
    """Append component review reason if applicable."""
    component = str(row.get("_ai_component_reason", "") or "")
    if component and component.lower() not in {"", "nan", "ok"}:
        parts.append(f"component:{component}")


class PipelineIO:
    """Handles data loading, saving, and progress tracking."""

    def __init__(self, cfg=None):
        self._cfg = cfg
        self._progress_file = "artifacts/matching/.progress"

    def read_table(self, path: str | Path) -> pd.DataFrame:
        """Read a CSV or Excel table as strings."""
        source_path = Path(path)
        if source_path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            return pd.read_excel(source_path, dtype=str)
        return pd.read_csv(source_path, encoding="utf-8-sig", dtype=str)

    def save_progress(self, drugs_df, start, end):
        """Save current progress (last completed row index) for --resume."""
        if drugs_df is None:
            return
        total = len(drugs_df)
        start = start or 0
        end = end or (start + total)
        progress = {
            "last_end": end,
            "total_loaded": total,
            "start": start,
        }
        Path(self._progress_file).parent.mkdir(parents=True, exist_ok=True)
        Path(self._progress_file).write_text(json.dumps(progress))
        logger.debug(f"Progress saved: last_end={end}")

    @staticmethod
    def load_progress() -> dict | None:
        """Load progress from previous run for --resume."""
        progress_file = "artifacts/matching/.progress"
        p = Path(progress_file)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def save_results(self, results, output_path, trace=None):
        """Save results to CSV."""
        if results is None:
            raise RuntimeError("No results to save")
        path = output_path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.public_results(results).to_csv(
            path, index=False, encoding="utf-8-sig",
        )
        logger.info(f"Saved to {path}")
        if trace and trace.enabled:
            trace.save()
        return path

    def save_manual_review(self, results, output_path, cfg):
        """Save unmatched and uncertain rows for manual review."""
        path = output_path.replace(".csv", "_manual_review.csv")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        review = self.manual_review_rows(results, cfg).copy()
        review["manual_review_reason"] = review.apply(
            _manual_review_reason_column, axis=1,
        )
        review["manual_decision"] = ""
        review["manual_reason"] = ""
        review["correct_store_product_id"] = ""
        self.public_results(review).to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"Manual review CSV saved to {path}")
        return path

    @staticmethod
    def public_results(results: pd.DataFrame) -> pd.DataFrame:
        """Drop internal helper columns before writing public CSV files."""
        return results.loc[:, [c for c in results.columns if not c.startswith("_")]]

    def manual_review_rows(self, results, cfg):
        """Extract rows that need manual review."""
        has_match = (
            results["matched_product_name_en"].notna()
            & (results["matched_product_name_en"] != "")
        )
        scores = pd.to_numeric(
            results["match_score"], errors="coerce",
        ).fillna(0)
        uncertain = has_match & (scores < cfg.ai_verify_threshold)
        component_review = (
            results["_ai_component_reason"].fillna("").astype(str) != ""
            if "_ai_component_reason" in results.columns
            else False
        )
        return results[(~has_match) | uncertain | component_review]


__all__ = [
    "_manual_review_path",
    "_manual_review_reason_column",
    "_manual_review_base_reasons",
    "_score_review_reasons",
    "_append_component_review_reason",
    "PipelineIO",
]
