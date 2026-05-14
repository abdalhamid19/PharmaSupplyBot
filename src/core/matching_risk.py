"""Risk-policy helpers for broad but reviewable Tawreed matches."""

from __future__ import annotations

from .candidate_identity import candidate_has_store_product_id
from .matching_models import CandidateMatchDiagnostic, MatchDecision, SearchMatch

AGGRESSIVE_MIN_SCORE = 12.0
AGGRESSIVE_MIN_OVERLAP = 0.45


def aggressive_review_decision(decision: MatchDecision) -> MatchDecision | None:
    """Return a flagged best candidate when safe matching found no winner."""
    if decision.best_match:
        return None
    diagnostic = _best_aggressive_diagnostic(decision.diagnostics)
    if diagnostic is None:
        return None
    return MatchDecision(
        _search_match(diagnostic),
        decision.diagnostics,
        _aggressive_reason(diagnostic),
    )


def is_aggressive_flagged_decision(decision: MatchDecision | None) -> bool:
    """Return whether a decision was produced by the aggressive policy."""
    return bool(decision and decision.final_reason.startswith("Aggressive flagged"))


def _best_aggressive_diagnostic(
    diagnostics: list[CandidateMatchDiagnostic],
) -> CandidateMatchDiagnostic | None:
    candidates = [
        diagnostic for diagnostic in diagnostics if _can_aggressively_flag(diagnostic)
    ]
    return max(candidates, key=lambda diagnostic: diagnostic.sort_key, default=None)


def _can_aggressively_flag(diagnostic: CandidateMatchDiagnostic) -> bool:
    return (
        candidate_has_store_product_id(diagnostic.candidate)
        and diagnostic.score >= AGGRESSIVE_MIN_SCORE
        and diagnostic.breakdown.overlap_score >= AGGRESSIVE_MIN_OVERLAP
    )


def _aggressive_reason(diagnostic: CandidateMatchDiagnostic) -> str:
    reason = diagnostic.rejection_reason or diagnostic.accepted_reason
    return (
        "Aggressive flagged match requires manual review: "
        f"score={diagnostic.score:.3f}; reason={reason}"
    )


def _search_match(diagnostic: CandidateMatchDiagnostic) -> SearchMatch:
    return SearchMatch(
        diagnostic.query,
        diagnostic.row_index,
        diagnostic.score,
        diagnostic.candidate,
    )
