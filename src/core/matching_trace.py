"""Shared structured tracing helpers for matching and AI decisions."""

from __future__ import annotations

import logging
import queue
from contextlib import contextmanager
from logging.handlers import QueueHandler, QueueListener
from typing import Any

from .matching_models import MatchDecision
from .matching_trace_fields import candidate_trace_fields, reason_code
from .utils.excel import Item

MAX_TRACE_CANDIDATE_ROWS = 25


def configure_async_logging(level: str = "INFO") -> tuple[logging.Logger, QueueListener]:
    """Configure a simple queue-backed logger for matching workflows."""
    log_queue: queue.Queue[logging.LogRecord] = queue.Queue()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    listener = QueueListener(log_queue, handler)
    listener.start()
    logger = logging.getLogger("pharmasupplybot.matching")
    logger.handlers = [QueueHandler(log_queue)]
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger, listener


@contextmanager
def async_matching_logging(level: str = "INFO"):
    """Run matching logging with a queue listener that is always stopped."""
    logger, listener = configure_async_logging(level)
    try:
        yield logger
    finally:
        listener.stop()

def decision_trace_rows(
    item: Item,
    decision: MatchDecision,
    phase: str = "matching",
) -> list[dict[str, Any]]:
    """Return candidate-level trace rows for one matching decision."""
    diagnostics = sorted(
        decision.diagnostics, key=lambda current: current.sort_key, reverse=True
    )[:MAX_TRACE_CANDIDATE_ROWS]
    if not diagnostics:
        return [_base_trace_row(item, decision, phase)]
    return [
        _candidate_trace_row(item, decision, phase, diagnostic, rank)
        for rank, diagnostic in enumerate(diagnostics, start=1)
    ]

def _base_trace_row(item: Item, decision: MatchDecision, phase: str) -> dict[str, Any]:
    return {
        "phase": phase, "item_code": item.code, "item_name": item.name,
        "item_qty": item.qty,
        "final_status": "matched" if decision.best_match else "no_match",
        "final_reason": decision.final_reason,
        "final_reason_code": reason_code(decision.final_reason),
        "candidate_rank": "", "candidate_name_en": "",
        "candidate_name_ar": "", "candidate_id": "",
        "candidate_has_orderable_id": "", "candidate_score": "",
        "accepted": "", "accepted_reason": "", "rejection_reason": "",
        "reason_code": "", "query": "", "row_index": "",
        "selection_reason": decision.final_reason,
    }

def _candidate_trace_row(
    item: Item,
    decision: MatchDecision,
    phase: str,
    diagnostic: CandidateMatchDiagnostic,
    rank: int,
) -> dict[str, Any]:
    row = _base_trace_row(item, decision, phase)
    row.update(candidate_trace_fields(diagnostic, rank))
    return row
