"""Main pipeline class structure and initialization."""

from .config import MatchingConfig, APIConfig, load_env
from .indexer import DrugIndex
from .trace_log import MatchTraceLog
from .pipeline_io import PipelineIO
from .pipeline_matching import PipelineMatching
from .pipeline_ai import PipelineAI


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
