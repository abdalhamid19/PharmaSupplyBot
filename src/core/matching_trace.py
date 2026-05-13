"""Shared structured tracing helpers for matching and AI decisions."""

from __future__ import annotations

import logging
import queue
from logging.handlers import QueueHandler, QueueListener
from typing import Any

from .matching_models import CandidateMatchDiagnostic, MatchDecision
from .utils.excel import Item


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

def decision_trace_rows(
    item: Item,
    decision: MatchDecision,
    phase: str = "matching",
) -> list[dict[str, Any]]:
    """Return candidate-level trace rows for one matching decision."""
    diagnostics = sorted(
        decision.diagnostics, key=lambda current: current.sort_key, reverse=True
    )
    if not diagnostics:
        return [_base_trace_row(item, decision, phase)]
    return [
        _candidate_trace_row(item, decision, phase, diagnostic, rank)
        for rank, diagnostic in enumerate(diagnostics, start=1)
    ]

def _base_trace_row(item: Item, decision: MatchDecision, phase: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "final_status": "matched" if decision.best_match else "no_match",
        "final_reason": decision.final_reason,
        "candidate_rank": "",
        "candidate_name_en": "",
        "candidate_name_ar": "",
        "candidate_id": "",
        "candidate_score": "",
        "accepted": "",
        "accepted_reason": "",
        "rejection_reason": "",
        "query": "",
        "row_index": "",
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
    row.update(_candidate_trace_fields(diagnostic, rank))
    return row

def _candidate_trace_fields(
    diagnostic: CandidateMatchDiagnostic, rank: int
) -> dict[str, Any]:
    return {
        "candidate_rank": rank,
        "candidate_name_en": _candidate_name(diagnostic, "productNameEn"),
        "candidate_name_ar": _candidate_name(diagnostic, "productName"),
        "candidate_id": diagnostic.candidate.get("storeProductId", ""),
        "candidate_score": round(diagnostic.score, 6),
        "accepted": diagnostic.accepted,
        "accepted_reason": diagnostic.accepted_reason,
        "rejection_reason": diagnostic.rejection_reason,
        "query": diagnostic.query,
        "row_index": diagnostic.row_index,
        "selection_reason": _candidate_selection_reason(diagnostic),
    }

def _candidate_name(diagnostic: CandidateMatchDiagnostic, key: str) -> str:
    return str(diagnostic.candidate.get(key) or "")


def _candidate_selection_reason(diagnostic: CandidateMatchDiagnostic) -> str:
    return diagnostic.accepted_reason if diagnostic.accepted else diagnostic.rejection_reason
