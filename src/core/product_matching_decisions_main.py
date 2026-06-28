"""Main decision logic for product matching."""

from .candidate_identity import candidate_store_product_id
from .matching_models import CandidateMatchDiagnostic, MatchDecision, SearchMatch
from .product_matching_decisions_builders import (
    _build_candidate_diagnostics,
    _apply_top_k_checks,
)
from .product_matching_decisions_diagnostics import (
    _rejected_diagnostic,
)


def _decision_from_diagnostics(
    diagnostics: list[CandidateMatchDiagnostic],
) -> MatchDecision:
    """Return the final match decision for an already-scored diagnostic list."""
    if not diagnostics:
        return _empty_match_decision()
    sorted_diagnostics = sorted(
        diagnostics, key=lambda diagnostic: diagnostic.sort_key, reverse=True
    )
    best_accepted = _best_accepted_diagnostic(sorted_diagnostics)
    if best_accepted is None:
        return _rejected_match_decision(diagnostics, sorted_diagnostics[0])
    ambiguity = _accepted_ambiguity_reason(sorted_diagnostics, best_accepted)
    if ambiguity:
        return MatchDecision(None, diagnostics, ambiguity)
    return _accepted_match_decision(diagnostics, best_accepted)


def _empty_match_decision() -> MatchDecision:
    """Return the no-candidates match decision."""
    return MatchDecision(
        best_match=None,
        diagnostics=[],
        final_reason="No search candidates were returned.",
    )


def _rejected_match_decision(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> MatchDecision:
    """Return a rejected match decision for the highest-ranked candidate."""
    return MatchDecision(
        best_match=None,
        diagnostics=diagnostics,
        final_reason=_rejected_decision_reason(best_diagnostic),
    )


def _accepted_match_decision(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> MatchDecision:
    """Return an accepted match decision for the highest-ranked accepted row."""
    return MatchDecision(
        best_match=_search_match(best_diagnostic),
        diagnostics=diagnostics,
        final_reason=_accepted_decision_reason(best_diagnostic),
    )


def _best_accepted_diagnostic(
    diagnostics: list[CandidateMatchDiagnostic],
) -> CandidateMatchDiagnostic | None:
    """Return the highest-ranked accepted diagnostic, if any."""
    for diagnostic in diagnostics:
        if diagnostic.accepted:
            return diagnostic
    return None


def _accepted_ambiguity_reason(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> str:
    tied_ids = _tied_accepted_ids(diagnostics, best_diagnostic)
    if len(tied_ids) <= 1:
        return ""
    return "Ambiguous accepted candidates: " + ", ".join(sorted(tied_ids))


def _tied_accepted_ids(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> set[str]:
    best_key = best_diagnostic.sort_key[:-1]
    return {
        candidate_store_product_id(diagnostic.candidate)
        for diagnostic in diagnostics
        if diagnostic.accepted and diagnostic.sort_key[:-1] == best_key
    }


def _rejected_decision_reason(best_diagnostic: CandidateMatchDiagnostic) -> str:
    """Return the message used when the best candidate fails acceptance rules."""
    return (
        best_diagnostic.rejection_reason
        or "Best candidate was rejected by acceptance rules."
    )


def _accepted_decision_reason(best_diagnostic: CandidateMatchDiagnostic) -> str:
    """Return the message used when the best candidate passes acceptance rules."""
    return f"Accepted best candidate because {best_diagnostic.accepted_reason}."


def _search_match(diagnostic: CandidateMatchDiagnostic) -> SearchMatch:
    """Return the public search-match object for one accepted diagnostic."""
    return SearchMatch(
        query=diagnostic.query,
        row_index=diagnostic.row_index,
        score=diagnostic.score,
        data=diagnostic.candidate,
    )
