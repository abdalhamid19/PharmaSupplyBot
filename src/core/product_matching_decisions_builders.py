"""Candidate diagnostic builders for product matching."""

from typing import Any

from .config.config_models import MatchingConfig
from .matching_models import CandidateMatchDiagnostic
from .utils.excel import Item
from .product_matching_decisions_diagnostics import _rejected_diagnostic


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
    from .product_matching_decisions_diagnostics import _diagnostic_record

    breakdown = _match_score_breakdown_for_config(score_query, result, matching_config)
    acceptance = _diagnostic_acceptance(
        score_query, result, breakdown, matching_config, skip_components
    )
    return _diagnostic_record(
        query, row_index, result, score_query, breakdown, acceptance
    )
