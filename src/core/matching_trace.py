"""Shared structured tracing helpers for matching and AI decisions."""

from __future__ import annotations

import logging
import queue
from contextlib import contextmanager
from logging.handlers import QueueHandler, QueueListener
from typing import Any

from .candidate_identity import candidate_store_product_id
from .matching_types import CandidateMatchDiagnostic, MatchDecision
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


def candidate_trace_fields(
    diagnostic: CandidateMatchDiagnostic, rank: int
) -> dict[str, Any]:
    """Return trace columns for one candidate diagnostic."""
    candidate_id = candidate_store_product_id(diagnostic.candidate)
    row = {
        "candidate_rank": rank, "candidate_id": candidate_id,
        "candidate_name_en": _candidate_name(diagnostic, "productNameEn"),
        "candidate_name_ar": _candidate_name(diagnostic, "productName"),
        "candidate_has_orderable_id": bool(candidate_id),
        "candidate_score": round(diagnostic.score, 6),
        "accepted": diagnostic.accepted, "accepted_reason": diagnostic.accepted_reason,
        "rejection_reason": diagnostic.rejection_reason,
        "reason_code": reason_code(_candidate_selection_reason(diagnostic)),
        "query": diagnostic.query, "row_index": diagnostic.row_index,
        "selection_reason": _candidate_selection_reason(diagnostic),
    }
    row.update(_score_breakdown_fields(diagnostic))
    return row


def reason_code(reason: object) -> str:
    """Return a compact grouping key for free-text trace reasons."""
    text = str(reason or "").strip().lower()
    if not text:
        return ""
    text = text.split(":", 1)[0]
    text = "".join(char if char.isalnum() else " " for char in text)
    return "_".join(text.replace("-", " ").split())


def _score_breakdown_fields(diagnostic: CandidateMatchDiagnostic) -> dict[str, Any]:
    breakdown = diagnostic.breakdown
    return {
        "score_sequence": round(breakdown.sequence_score, 6),
        "score_overlap": round(breakdown.overlap_score, 6),
        "score_numeric_overlap": round(breakdown.numeric_overlap, 6),
        "score_exact_bonus": round(breakdown.exact_bonus, 6),
        "score_availability_bonus": round(breakdown.availability_bonus, 6),
        "score_critical_penalty": round(breakdown.critical_penalty, 6),
        "score_extra_token_penalty": round(breakdown.extra_token_penalty, 6),
        "score_semantic_penalty": round(breakdown.semantic_penalty, 6),
    }


def _candidate_name(diagnostic: CandidateMatchDiagnostic, key: str) -> str:
    return str(diagnostic.candidate.get(key) or "")


def _candidate_selection_reason(diagnostic: CandidateMatchDiagnostic) -> str:
    if diagnostic.accepted:
        return diagnostic.accepted_reason
    return diagnostic.rejection_reason
