"""Decision logic and diagnostics for product matching."""

from __future__ import annotations

from typing import Any

from .candidate_identity import candidate_store_product_id
from .config.config_models import MatchingConfig
from .matching_models import CandidateMatchDiagnostic, MatchDecision, SearchMatch
from .utils.excel import Item


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


def _candidate_diagnostic(
    score_query: str,
    query: str,
    row_index: int,
    result: dict[str, Any],
    matching_config: MatchingConfig,
    skip_components: bool = False,
) -> CandidateMatchDiagnostic:
    """Return one diagnostic record for a candidate result row."""
    from .product_matching_acceptance import _diagnostic_acceptance
    from .product_matching_scoring import _match_score_breakdown_for_config

    breakdown = _match_score_breakdown_for_config(score_query, result, matching_config)
    acceptance = _diagnostic_acceptance(
        score_query, result, breakdown, matching_config, skip_components
    )
    return _diagnostic_record(
        query, row_index, result, score_query, breakdown, acceptance
    )


def _diagnostic_record(
    query: str,
    row_index: int,
    result: dict[str, Any],
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


def _build_candidate_diagnostics(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig,
) -> list[CandidateMatchDiagnostic]:
    """Build diagnostics for every search result candidate considered."""
    from .product_matching_acceptance import _iter_results

    diagnostics: list[CandidateMatchDiagnostic] = []
    for query, row_index, result in _iter_results(search_results_by_query):
        diagnostics.append(
            _candidate_diagnostic(
                item.name or query,
                query,
                row_index,
                result,
                matching_config,
                skip_components=True,
            )
        )
    sorted_diags = sorted(diagnostics, key=lambda d: d.sort_key, reverse=True)
    return _apply_top_k_checks(item, sorted_diags, matching_config.candidate_top_k)


def _apply_top_k_checks(item: Item, sorted_diags: list, top_k: int) -> list:
    """Apply expensive component checks on sorted candidates using top-k logic."""
    from .product_matching_acceptance import _candidate_component_rejection

    accepted_count, final = 0, []
    for d in sorted_diags:
        if not d.accepted:
            final.append(d)
        elif accepted_count < top_k or not any(x.accepted for x in final):
            rejection = _candidate_component_rejection(
                item.name or d.query, d.candidate
            )
            if rejection:
                final.append(_rejected_diagnostic(d, rejection))
            else:
                final.append(d)
                accepted_count += 1
        else:
            final.append(
                _rejected_diagnostic(d, "Skipped by candidate top-k optimization")
            )
    return final


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
