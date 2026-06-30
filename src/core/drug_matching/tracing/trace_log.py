"""Detailed algorithm trace logger - CSV + TXT output.

This module provides the main MatchTraceLog interface and delegates
specialized logging to helper modules:
- trace_log_candidate_scoring.py: Candidate generation and scoring events
- trace_log_ai.py: AI verification, search, and review events
- trace_log_summary.py: Summary generation and output writing
- trace_log_phases.py: Phase 1, 2 & 3 algorithmic and AI steps
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .trace_log_candidate_scoring import (
    CandidateEventLogger,
    ScoringEventLogger,
)
from .trace_log_ai import AIEventLogger
from .trace_log_summary import SummaryWriter
from .trace_log_output import TraceOutputWriter
from .trace_log_phases import Phase1Methods, Phase2Methods

logger = logging.getLogger("pharmasupplybot.matching")

TRACE_MINIMAL = 1
TRACE_NORMAL = 2
TRACE_VERBOSE = 3


class MatchTraceLog(Phase1Methods, Phase2Methods):
    """Records every algorithmic + AI step for debugging.

    This class coordinates specialized loggers for different event types
    and provides a unified interface for trace logging.
    """

    TRACE_MINIMAL = TRACE_MINIMAL
    TRACE_NORMAL = TRACE_NORMAL
    TRACE_VERBOSE = TRACE_VERBOSE

    __slots__ = ("_rows", "_dir", "_enabled", "_run_id", "_level",
                 "_candidate_logger", "_scoring_logger", "_ai_logger",
                 "_output_writer")

    def __init__(
        self, log_dir: str | None = None, enabled: bool = True,
        level: int = TRACE_NORMAL,
    ):
        self._enabled = enabled
        self._level = level
        self._rows: list[dict] = []
        self._dir = Path(log_dir) if log_dir else Path("artifacts/matching/trace")
        self._run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        if enabled:
            self._dir.mkdir(parents=True, exist_ok=True)

        self._candidate_logger = CandidateEventLogger(self)
        self._scoring_logger = ScoringEventLogger(self)
        self._ai_logger = AIEventLogger(self)
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
        """Create base row with common fields."""
        row_index = extra.pop("row_index", "")
        row = {
            "run_id": self._run_id, "row_index": row_index,
            "drug_code": code, "drug_name": name,
            "norm": norm, "brand": brand,
        }
        for key, value in extra.items():
            if value not in (None, ""):
                row[key] = value
        return row

    def _append(self, code, name, norm, brand, **extra):
        """Append a row to the trace log."""
        if not self._enabled:
            return
        self._rows.append(self._base(code, name, norm, brand, **extra))

    @staticmethod
    def components_text(comp) -> str:
        """Format drug components as text for logging."""
        if not comp:
            return ""
        return (
            f"brand={comp.brand}; dosage={comp.dosage_nums or '-'}; "
            f"qty={comp.qty or '-'}; volume={comp.volume or '-'}; "
            f"weight={comp.weight or '-'}; form={comp.form or '-'}; "
            f"flavor={comp.flavor or '-'}; "
            f"imported={'yes' if comp.imported else 'no'}"
        )

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        """Save trace files (CSV, TXT, and summary)."""
        return self._output_writer.save(prefix)

    def save_summary(self, path: Path):
        """Save summary CSV to the given path."""
        summary_writer = SummaryWriter(self)
        summary_writer.save_summary(path)
