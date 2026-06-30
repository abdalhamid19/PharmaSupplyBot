"""AI steps for the pipeline."""

from __future__ import annotations

import pandas as pd

from ..config import MatchingConfig, APIConfig
from ..indexing.indexer import DrugIndex
from ..ai.ai_steps import run_ai_verification, run_ai_search, run_ai_review


class PipelineAI:
    """Phase 2 & 3 AI verification and search logic."""

    def __init__(self, cfg: MatchingConfig, api_cfg: APIConfig, index: DrugIndex, trace):
        self._cfg = cfg
        self._api_cfg = api_cfg
        self._index = index
        self._trace = trace
        self._results: pd.DataFrame | None = None

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

    def _require_results(self):
        if self._results is None:
            raise RuntimeError("Call run_matching() first")


__all__ = ["PipelineAI"]
