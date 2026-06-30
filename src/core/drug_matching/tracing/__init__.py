"""Trace logging subsystem for drug matching.

This package contains all trace log modules that record detailed
algorithmic and AI steps during drug matching for debugging and analysis.

Main entry point:
- MatchTraceLog: Main trace logger interface

Specialized loggers:
- trace_log_candidate_scoring: Candidate generation and scoring events
- trace_log_ai: AI verification, search, and review events
- trace_log_summary: Summary generation and output writing
- trace_log_phases: Phase 1, 2 & 3 algorithmic and AI steps
- trace_log_output: CSV and TXT output writing
- trace_log_output_writers: Writer classes for trace log output
- trace_log_ai_logging: AI logging methods for verify, search, review
- trace_log_ai_mixins: Mix-in classes for AI rotation logging
- trace_log_ai_records: AI record types and event logger
"""

from .trace_log import MatchTraceLog
from .trace_log import TRACE_MINIMAL, TRACE_NORMAL, TRACE_VERBOSE

__all__ = [
    "MatchTraceLog",
    "TRACE_MINIMAL",
    "TRACE_NORMAL",
    "TRACE_VERBOSE",
]
