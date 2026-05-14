"""Field builders for matching trace rows."""
from __future__ import annotations

from typing import Any

from .candidate_identity import candidate_store_product_id
from .matching_models import CandidateMatchDiagnostic


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
