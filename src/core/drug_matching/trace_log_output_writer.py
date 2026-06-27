"""Output writing for trace log (CSV and TXT)."""

from datetime import datetime
from pathlib import Path

from .trace_log_summary_writer import SummaryWriter
from .trace_log_output_csv import TraceCSVWriter
from .trace_log_output_txt import TraceTXTWriter


class TraceOutputWriter:
    """Handles CSV and TXT output writing for trace logs."""

    def __init__(self, parent_logger):
        """Initialize with reference to parent MatchTraceLog instance."""
        self._parent = parent_logger
        self._csv_writer = TraceCSVWriter(parent_logger)
        self._txt_writer = TraceTXTWriter(parent_logger)

    def save(self, prefix: str = "trace") -> tuple[str, str, str]:
        """Save trace files (CSV, TXT, and summary)."""
        if not self._parent._enabled or not self._parent._rows:
            return "", "", ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = self._parent._dir / f"{prefix}_{ts}.csv"
        txt_path = self._parent._dir / f"{prefix}_{ts}.txt"
        summary_path = self._parent._dir / f"{prefix}_summary_{ts}.csv"
        self._csv_writer.save_csv(csv_path)
        self._txt_writer.save_txt(txt_path)
        summary_writer = SummaryWriter(self._parent)
        summary_writer.save_summary(summary_path)
        import logging
        logger = logging.getLogger("pharmasupplybot.matching")
        logger.info(
            f"Trace saved: {csv_path} + {txt_path} + {summary_path}",
        )
        return str(csv_path), str(txt_path), str(summary_path)


__all__ = ["TraceOutputWriter"]
