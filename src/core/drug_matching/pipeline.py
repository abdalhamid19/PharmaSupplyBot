"""Full matching pipeline with optional AI verification."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .config import MatchingConfig, APIConfig, Paths, load_env
from .indexer import DrugIndex
from .trace_log import MatchTraceLog

logger = logging.getLogger("pharmasupplybot.matching")

# Constants
_RESULT_COLS = [
    "code", "drug_name", "matched_product_name_en",
    "matched_product_name_ar", "matched_store_product_id",
    "match_score", "verified", "match_method", "ai_confidence", "ai_review_confidence",
]


# Helper functions
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


# I/O operations
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


# Matching logic
class PipelineMatching:
    """Phase 1 algorithmic matching logic."""

    def __init__(self, cfg: MatchingConfig, index: DrugIndex, trace, io: PipelineIO):
        self._cfg = cfg
        self._index = index
        self._trace = trace
        self._io = io
        self._drugs_df: pd.DataFrame | None = None
        self._results: pd.DataFrame | None = None
        self._matching_engine = None

    def load_data(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
        limit: int | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        """Load and prepare data sources."""
        paths = Paths()
        drugs_path = drugs_path or paths.drugs_csv
        tawreed_path = tawreed_path or paths.tawreed_csv
        drugs_raw = self._io.read_table(drugs_path)
        drugs = drugs_raw.iloc[:, [0, 1]].copy()
        drugs.columns = ["code", "drug_name"]
        drugs["drug_price"] = (
            drugs_raw.iloc[:, 2] if drugs_raw.shape[1] > 2 else ""
        )
        tawreed = self._io.read_table(tawreed_path)
        if start is not None or end is not None:
            s = start or 0
            e = end or len(drugs)
            drugs = drugs.iloc[s:e].reset_index(drop=True)
            logger.info(f"Slice applied: rows {s}-{e-1} ({len(drugs)} drugs)")
        if limit:
            drugs = drugs.head(limit)
            logger.info(f"Limit applied: processing {len(drugs)} drugs")
        self._drugs_df = drugs
        logger.info(
            f"Loaded {len(drugs)} drugs, "
            f"{self._index.size} tawreed products",
        )

    def run_matching(self) -> pd.DataFrame:
        """Algorithmic matching using brand index + fuzzy search."""
        self._require_data()
        results = []
        stats = {"brand_index": 0, "fuzzy": 0, "no_match": 0}
        for row_index, row in enumerate(self._drugs_df.itertuples(index=False)):
            rec, score, method = self._match_one(row, stats, row_index)
            results.append(self._make_row(row, rec, score, method, stats))
        self._results = pd.DataFrame(results, columns=_RESULT_COLS if not results else None)
        # Allow mixed str/float in numeric-optional columns
        for col in ("match_score", "ai_confidence", "ai_review_confidence"):
            if col in self._results.columns:
                self._results[col] = self._results[col].astype(object)
        logger.info(f"Phase 1 done: {stats}")
        self._log_match_counts()
        return self._results

    def _log_match_counts(self):
        """Log matching statistics."""
        matched = self._results[
            self._results["matched_product_name_en"] != ""
        ]
        total = len(self._results)
        logger.info(
            f"  Matched: {len(matched)}, "
            f"Not matched: {total - len(matched)}",
        )

    def _require_data(self):
        if self._drugs_df is None:
            raise RuntimeError("Call load_data() first")

    def _match_one(self, row, stats, row_index):
        """Match one drug record."""
        rec, score, method = self._index.best_match(row.drug_name)
        if rec is not None:
            if method in ("component_index", "brand_index"):
                stats["brand_index"] += 1
            else:
                stats["fuzzy"] += 1
        else:
            stats["no_match"] += 1
        return rec, score, method

    def _make_row(self, row, rec, score, method, stats):
        """Build one result row."""
        if rec is None:
            return {
                "code": row.code,
                "drug_name": row.drug_name,
                "matched_product_name_en": "",
                "matched_product_name_ar": "",
                "matched_store_product_id": "",
                "match_score": 0.0,
                "verified": "",
                "match_method": method,
                "ai_confidence": "",
                "ai_review_confidence": "",
            }
        return {
            "code": row.code,
            "drug_name": row.drug_name,
            "matched_product_name_en": rec.get("productNameEn", ""),
            "matched_product_name_ar": rec.get("productName", ""),
            "matched_store_product_id": rec.get("storeProductId", ""),
            "match_score": score,
            "verified": "",
            "match_method": method,
            "ai_confidence": "",
            "ai_review_confidence": "",
        }


# Main pipeline class
class MatchPipeline:
    """Full matching pipeline with optional AI verification."""

    __slots__ = (
        "_cfg", "_api_cfg", "_index", "_limit", "_start", "_end", "_trace",
        "_io", "_matching", "_ai",
    )

    def __init__(
        self,
        cfg: MatchingConfig | None = None,
        api_cfg: APIConfig | None = None,
        limit: int | None = None,
        start: int | None = None,
        end: int | None = None,
    ):
        load_env()
        self._cfg = cfg or MatchingConfig()
        self._api_cfg = api_cfg or APIConfig()
        self._limit = limit
        self._start = start
        self._end = end
        self._index: DrugIndex | None = None
        self._trace: MatchTraceLog | None = None
        self._io = PipelineIO(self._cfg)
        self._matching = None
        self._ai = None

    def load_data(self, drugs_path: str | None = None, tawreed_path: str | None = None):
        """Load and prepare data sources."""
        if self._index is None:
            paths = Paths()
            tawreed_path = tawreed_path or paths.tawreed_csv
            tawreed = self._io.read_table(tawreed_path)
            self._index = DrugIndex(tawreed, self._cfg)
        self._matching = PipelineMatching(self._cfg, self._index, self._trace, self._io)
        self._matching.load_data(drugs_path, tawreed_path, self._limit, self._start, self._end)
        if self._ai is None:
            from .pipeline_ai import PipelineAI
            self._ai = PipelineAI(self._cfg, self._api_cfg, self._index, self._trace)

    def run_matching(self) -> pd.DataFrame:
        """Algorithmic matching using brand index + fuzzy search."""
        if self._matching is None:
            raise RuntimeError("Call load_data() first")
        return self._matching.run_matching()

    def save_progress(self):
        """Save current progress (last completed row index) for --resume."""
        if self._matching:
            self._io.save_progress(self._matching._drugs_df, self._start, self._end)

    @staticmethod
    def load_progress() -> dict | None:
        """Load progress from previous run for --resume."""
        return PipelineIO.load_progress()

    def save(self, output_path: str | None = None) -> str:
        """Save results to CSV."""
        if self._matching is None or self._matching._results is None:
            raise RuntimeError("No results to save")
        path = output_path or str(Paths().output_csv)
        saved_path = self._io.save_results(self._matching._results, path, self._trace)
        self.save_progress()
        return saved_path

    def save_manual_review(self, output_path: str | None = None) -> str:
        """Save unmatched and uncertain rows for manual review."""
        if self._matching is None or self._matching._results is None:
            raise RuntimeError("No results to save")
        path = output_path or str(Paths().output_csv)
        path = _manual_review_path(path)
        return self._io.save_manual_review(self._matching._results, path, self._cfg)

    def print_stats(self):
        """Print final statistics."""
        if self._matching is None or self._matching._results is None:
            return
        results = self._matching._results
        total = len(results)
        has_match = (
            results["matched_product_name_en"].notna()
            & (results["matched_product_name_en"] != "")
        )
        matched = results[has_match]
        not_matched = results[~has_match]
        logger.info("=" * 50)
        logger.info("FINAL RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total drugs: {total}")
        matched_pct = len(matched) / total * 100
        logger.info(f"Matched: {len(matched)} ({matched_pct:.1f}%)")
        not_matched_pct = len(not_matched) / total * 100
        logger.info(f"Not matched: {len(not_matched)} ({not_matched_pct:.1f}%)")
        if len(matched) > 0:
            self._log_score_dist(matched)
        logger.info("Verification breakdown:")
        logger.info(results["verified"].value_counts(dropna=False).to_string())
        logger.info("Method breakdown:")
        logger.info(results["match_method"].value_counts(dropna=False).to_string())

    def _log_score_dist(self, matched):
        """Log score distribution."""
        scores = pd.to_numeric(matched["match_score"], errors="coerce")
        logger.info("Score distribution:")
        for label, lo, hi in [
            ("100", 100, 101), ("95-99", 95, 100),
            ("90-94", 90, 95), ("80-89", 80, 90),
            ("70-79", 70, 80),
        ]:
            count = ((scores >= lo) & (scores < hi)).sum()
            logger.info(f"  {label}: {count}")
        logger.info(f"  <70: {(scores < 70).sum()}")

    async def run_ai_verification(self) -> pd.DataFrame:
        """AI verification of matches below threshold."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_verification()

    async def run_ai_search_unmatched(self) -> pd.DataFrame:
        """AI searches for matches among unmatched items."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_search_unmatched()

    async def run_ai_review(self) -> pd.DataFrame:
        """AI review: second model cross-verifies low-confidence AI decisions."""
        if self._ai is None:
            raise RuntimeError("Call load_data() first")
        return await self._ai.run_ai_review()

    async def run_full(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
        output_path: str | None = None,
        skip_ai: bool = False,
    ) -> pd.DataFrame:
        """Run the complete pipeline."""
        self.load_data(drugs_path, tawreed_path)
        self.run_matching()
        if not skip_ai:
            await self.run_ai_verification()
            await self.run_ai_search_unmatched()
            await self.run_ai_review()
        saved_path = self.save(output_path)
        self.save_manual_review(_manual_review_path(saved_path))
        self.print_stats()
        return self._matching._results


__all__ = ["MatchPipeline"]
