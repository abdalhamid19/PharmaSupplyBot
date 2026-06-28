"""Diagnostic record utilities for product matching."""

from .matching_models import CandidateMatchDiagnostic


def _diagnostic_record(
    query: str,
    row_index: int,
    result: dict,
    score_query: str,
    breakdown,
    acceptance: tuple[bool, str, str],
) -> CandidateMatchDiagnostic:
    """Return the final diagnostic dataclass for one candidate result row."""
    from .product_matching_scoring import _match_sort_key

    return CandidateMatchDiagnostic(
        query=query,
        row_index=row_index,
        score=breakdown.total_score,
        sort_key=_match_sort_key(score_query, result, breakdown.total_score),
        accepted=acceptance[0],
        accepted_reason=acceptance[1],
        rejection_reason=acceptance[2],
        breakdown=breakdown,
        candidate=result,
    )


def _rejected_diagnostic(
    d: CandidateMatchDiagnostic, reason: str
) -> CandidateMatchDiagnostic:
    """Return a modified diagnostic reflecting a new rejection reason."""
    return CandidateMatchDiagnostic(
        query=d.query,
        row_index=d.row_index,
        score=d.score,
        sort_key=d.sort_key,
        accepted=False,
        accepted_reason="",
        rejection_reason=reason,
        breakdown=d.breakdown,
        candidate=d.candidate,
    )
