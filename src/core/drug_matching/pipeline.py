"""Pipeline orchestrator - coordinates matching, verification, and output."""
import logging
from pathlib import Path

import pandas as pd

from .config import MatchingConfig, APIConfig, Paths, load_env
from .indexer import DrugIndex
from .ai_steps import run_ai_verification, run_ai_search, run_ai_review
from .trace_log import MatchTraceLog
from .pipeline_matching import MatchingEngine
from .pipeline_io import PipelineIO
from .pipeline_helpers import _manual_review_path

logger = logging.getLogger("pharmasupplybot.matching")

_RESULT_COLS = [
    "code", "drug_name", "matched_product_name_en",
    "matched_product_name_ar", "matched_store_product_id",
    "match_score", "verified", "match_method", "ai_confidence", "ai_review_confidence",
]


class MatchPipeline:
    """Full matching pipeline with optional AI verification."""

    __slots__ = (
        "_cfg", "_api_cfg", "_drugs_df", "_index",
        "_results", "_limit", "_start", "_end", "_trace",
        "_matching_engine", "_io",
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
        self._drugs_df: pd.DataFrame | None = None
        self._index: DrugIndex | None = None
        self._results: pd.DataFrame | None = None
        self._trace: MatchTraceLog | None = None
        self._matching_engine = None
        self._io = PipelineIO(self._cfg)

    # --- data loading ---

    def load_data(
        self, drugs_path: str | None = None,
        tawreed_path: str | None = None,
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
        if self._start is not None or self._end is not None:
            s = self._start or 0
            e = self._end or len(drugs)
            drugs = drugs.iloc[s:e].reset_index(drop=True)
            logger.info(f"Slice applied: rows {s}-{e-1} ({len(drugs)} drugs)")
        if self._limit:
            drugs = drugs.head(self._limit)
            logger.info(f"Limit applied: processing {len(drugs)} drugs")
        self._drugs_df = drugs
        self._index = DrugIndex(tawreed, self._cfg)
        self._matching_engine = MatchingEngine(self._cfg, self._index, self._trace)
        logger.info(
            f"Loaded {len(drugs)} drugs, "
            f"{self._index.size} tawreed products",
        )

    # --- Phase 1: algorithmic matching ---

    def run_matching(self) -> pd.DataFrame:
        """Algorithmic matching using brand index + fuzzy search."""
        self._require_data()
        results = []
        stats = {"brand_index": 0, "fuzzy": 0, "no_match": 0}
        for row_index, row in enumerate(self._drugs_df.itertuples(index=False)):
            rec, score, method = self._matching_engine.match_one(row, stats, row_index)
            results.append(self._matching_engine.make_row(row, rec, score, method, stats))
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

    # --- Phase 2 & 3: AI steps (delegated) ---

    async def run_ai_verification(self) -> pd.DataFrame:
        """AI verification of matches below threshold."""
        self._require_results()
        self._results = await run_ai_verification(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    async def run_ai_search_unmatched(self) -> pd.DataFrame:
        """AI searches for matches among unmatched items."""
        self._require_results()
        self._results = await run_ai_search(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    async def run_ai_review(self) -> pd.DataFrame:
        """AI review: second model cross-verifies low-confidence AI decisions."""
        self._require_results()
        self._results = await run_ai_review(
            self._results, self._index, self._cfg, self._api_cfg,
            trace=self._trace,
        )
        return self._results

    # --- save & stats ---

    def save_progress(self):
        """Save current progress (last completed row index) for --resume."""
        self._io.save_progress(self._drugs_df, self._start, self._end)

    @staticmethod
    def load_progress() -> dict | None:
        """Load progress from previous run for --resume."""
        return PipelineIO.load_progress()

    def save(self, output_path: str | None = None) -> str:
        """Save results to CSV."""
        if self._results is None:
            raise RuntimeError("No results to save")
        path = output_path or str(Paths().output_csv)
        saved_path = self._io.save_results(self._results, path, self._trace)
        self.save_progress()
        return saved_path

    def save_manual_review(self, output_path: str | None = None) -> str:
        """Save unmatched and uncertain rows for manual review."""
        self._require_results()
        path = output_path or str(Paths().output_csv)
        path = _manual_review_path(path)
        return self._io.save_manual_review(self._results, path, self._cfg)

    def print_stats(self):
        """Print final statistics."""
        if self._results is None:
            return
        total = len(self._results)
        has_match = (
            self._results["matched_product_name_en"].notna()
            & (self._results["matched_product_name_en"] != "")
        )
        matched = self._results[has_match]
        not_matched = self._results[~has_match]
        logger.info("=" * 50)
        logger.info("FINAL RESULTS")
        logger.info("=" * 50)
        logger.info(f"Total drugs: {total}")
        logger.info(
            f"Matched: {len(matched)} "
            f"({len(matched)/total*100:.1f}%)",
        )
        logger.info(
            f"Not matched: {len(not_matched)} "
            f"({len(not_matched)/total*100:.1f}%)",
        )
        if len(matched) > 0:
            self._log_score_dist(matched)
        logger.info("Verification breakdown:")
        logger.info(
            self._results["verified"]
            .value_counts(dropna=False).to_string(),
        )
        logger.info("Method breakdown:")
        logger.info(
            self._results["match_method"]
            .value_counts(dropna=False).to_string(),
        )

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

    # --- full pipeline ---

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
        return self._results

    # --- guards ---

    def _require_data(self):
        if self._drugs_df is None or self._index is None:
            raise RuntimeError("Call load_data() first")

    def _require_results(self):
        if self._results is None:
            raise RuntimeError("Call run_matching() first")


__all__ = ["MatchPipeline"]
