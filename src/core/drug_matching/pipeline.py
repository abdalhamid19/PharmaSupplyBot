"""Pipeline orchestrator - coordinates matching, verification, and output."""

from .pipeline_main import MatchPipeline as _MatchPipelineBase
from .pipeline_data import PipelineDataMixin
from .pipeline_ai_steps import PipelineAIMixin
from .pipeline_output import PipelineOutputMixin
from .pipeline_full import PipelineFullMixin


class MatchPipeline(
    _MatchPipelineBase,
    PipelineDataMixin,
    PipelineAIMixin,
    PipelineOutputMixin,
    PipelineFullMixin,
):
    """Full matching pipeline with optional AI verification."""
    pass


__all__ = ["MatchPipeline"]
