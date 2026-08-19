"""Detailed trace logger for deterministic product matching."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .trace_log_candidate_scoring import CandidateEventLogger, ScoringEventLogger
from .trace_log_output import TraceOutputWriter
from .trace_log_phases import Phase1Methods

TRACE_MINIMAL = 1
TRACE_NORMAL = 2
TRACE_VERBOSE = 3


class MatchTraceLog(Phase1Methods):
    """Records local normalization, candidate, scoring, and final-match steps."""

    TRACE_MINIMAL = TRACE_MINIMAL
    TRACE_NORMAL = TRACE_NORMAL
    TRACE_VERBOSE = TRACE_VERBOSE

    __slots__ = (
        "_rows", "_dir", "_enabled", "_run_id", "_level",
        "_candidate_logger", "_scoring_logger", "_output_writer",
    )

    def __init__(self, log_dir: str | None = None, enabled: bool = True, level: int = TRACE_NORMAL):
        self._enabled = enabled
        self._level = level
        self._rows: list[dict] = []
        self._dir = Path(log_dir) if log_dir else Path("artifacts/matching/trace")
        self._run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)
        self._candidate_logger = CandidateEventLogger(self)
        self._scoring_logger = ScoringEventLogger(self)
        self._output_writer = TraceOutputWriter(self)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def level(self) -> int:
        return self._level

    @property
    def verbose(self) -> bool:
        return self._level >= TRACE_VERBOSE

    def _base(self, code, name, norm, brand, **extra):
        row = {
            "run_id": self._run_id, "row_index": extra.pop("row_index", ""),
            "drug_code": code, "drug_name": name, "norm": norm, "brand": brand,
        }
        row.update({key: value for key, value in extra.items() if value not in (None, "")})
        return row

    def _append(self, code, name, norm, brand, **extra):
        if self._enabled:
            self._rows.append(self._base(code, name, norm, brand, **extra))

    @staticmethod
    def components_text(comp) -> str:
        if not comp:
            return ""
        return f"brand={comp.brand}; dosage={comp.dosage_nums or '-'}; form={comp.form or '-'}"

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        return self._output_writer.save(prefix)

    def save_summary(self, path: Path):
        from .trace_log_summary import SummaryWriter
        SummaryWriter(self).save_summary(path)
