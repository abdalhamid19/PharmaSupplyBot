"""Decision logic for Tawreed product matching logs."""

from __future__ import annotations

from ..core.matching_models import CandidateMatchDiagnostic, MatchDecision


def should_write_detailed_match_log(decision: MatchDecision) -> bool:
    """Return whether one decision needs full diagnostic logging for later review."""
    if not decision.best_match:
        return True
    best_diagnostic = _best_match_diagnostic(decision)
    if best_diagnostic is None:
        return True
    if not best_diagnostic.accepted:
        return True
    if best_diagnostic.accepted_reason != "high_token_overlap":
        return True
    if best_diagnostic.breakdown.overlap_score < 1.0:
        return True
    if best_diagnostic.breakdown.numeric_overlap not in (0.0, 1.0):
        return True
    return False


def _best_match_diagnostic(decision: MatchDecision) -> CandidateMatchDiagnostic | None:
    """Return the diagnostic that corresponds to the accepted best match."""
    best_match = decision.best_match
    if best_match is None:
        return None
    for diagnostic in decision.diagnostics:
        if diagnostic.query != best_match.query:
            continue
        if diagnostic.row_index != best_match.row_index:
            continue
        return diagnostic
    return None
