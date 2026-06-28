"""Data loading and matching methods for MatchPipeline."""

import pandas as pd

from .config import Paths
from .indexer import DrugIndex
from .pipeline_matching import PipelineMatching
from .pipeline_ai import PipelineAI


class PipelineDataMixin:
    """Data loading and matching methods for MatchPipeline."""

    def load_data(self, drugs_path: str | None = None, tawreed_path: str | None = None):
        """Load and prepare data sources."""
        if self._index is None:
            paths = Paths()
            tawreed_path = tawreed_path or paths.tawreed_csv
            tawreed = self._io.read_table(tawreed_path)
            self._index = DrugIndex(tawreed, self._cfg)
        self._matching = PipelineMatching(self._cfg, self._index, self._trace, self._io)
        self._matching.load_data(drugs_path, tawreed_path, self._limit, self._start, self._end)
        self._ai = PipelineAI(self._cfg, self._api_cfg, self._index, self._trace)

    def run_matching(self) -> pd.DataFrame:
        """Algorithmic matching using brand index + fuzzy search."""
        if self._matching is None:
            raise RuntimeError("Call load_data() first")
        return self._matching.run_matching()
