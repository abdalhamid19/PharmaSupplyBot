"""Full matching pipeline with optional AI verification - re-exports from split modules."""

from __future__ import annotations

import logging

from .config import MatchingConfig, APIConfig, Paths, load_env
from .indexing.indexer import DrugIndex
from .tracing.trace_log import MatchTraceLog

# Re-export from split modules
from .pipeline_components.pipeline_io import (
    _manual_review_path,
    _manual_review_reason_column,
    _manual_review_base_reasons,
    _score_review_reasons,
    _append_component_review_reason,
    PipelineIO,
)
from .pipeline_components.pipeline_matching import (
    _RESULT_COLS,
    PipelineMatching,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Main pipeline class
# ============================================================================

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
            from .pipeline_components.pipeline_ai import PipelineAI
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
