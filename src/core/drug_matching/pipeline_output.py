"""Save and statistics methods for MatchPipeline."""

import logging

import pandas as pd

from .config import Paths
from .pipeline_io import PipelineIO
from .pipeline_helpers import _manual_review_path


class PipelineOutputMixin:
    """Save and statistics methods for MatchPipeline."""

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
        logger = logging.getLogger("pharmasupplybot.matching")
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
        logger = logging.getLogger("pharmasupplybot.matching")
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
