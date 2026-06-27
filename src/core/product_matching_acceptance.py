"""Acceptance and rejection rules for product matching."""

from __future__ import annotations

from typing import Any

from .config.config_models import MatchingConfig
from .matching_models import MatchScoreBreakdown
from .matching_penalties import compatibility_rejection_reason
from .product_matching_components import _candidate_component_rejection
from .product_matching_identity import _candidate_variant_rejection
from .product_matching_numeric import _numeric_safe_acceptance
from .product_matching_orderable import _orderable_acceptance


def _diagnostic_acceptance(
    score_query: str,
    result: dict[str, Any],
    breakdown: MatchScoreBreakdown,
    matching_config: MatchingConfig,
    skip_components: bool = False,
) -> tuple[bool, str, str]:
    """Return the acceptance outcome for one candidate diagnostic."""
    variant_rejection = _candidate_variant_rejection(score_query, result)
    if variant_rejection:
        return False, "", variant_rejection
    lexical = _lexical_or_threshold_acceptance(
        score_query, result, breakdown, matching_config
    )
    if lexical[2] or skip_components:
        return lexical if lexical[2] else _orderable_acceptance(result, lexical)
    rejection = _candidate_component_rejection(score_query, result)
    if rejection:
        return False, "", rejection
    return _orderable_acceptance(result, lexical)


def _lexical_or_threshold_acceptance(
    score_query: str,
    result: dict[str, Any],
    breakdown: MatchScoreBreakdown,
    matching_config: MatchingConfig,
) -> tuple[bool, str, str]:
    """Return lexical rejection or the standard threshold acceptance outcome."""
    from .product_matching_scoring import _candidate_english_name

    lexical_rejection = compatibility_rejection_reason(
        score_query, _candidate_english_name(result)
    )
    if lexical_rejection:
        return False, "", lexical_rejection
    from .matching_rules import acceptance_details

    acceptance = acceptance_details(
        score_query,
        result,
        breakdown.total_score,
        matching_config,
        _matching_rule_helpers(),
    )
    return _numeric_safe_acceptance(score_query, result, acceptance)


def _matching_rule_helpers() -> tuple:
    from .product_matching_scoring import (
        _best_candidate_overlap,
        _candidate_english_name,
        _normalize_text,
        _numeric_match_count,
    )

    return (
        _normalize_text,
        _candidate_english_name,
        _best_candidate_overlap,
        _numeric_match_count,
    )


def _candidate_dedupe_key(result: dict[str, Any]) -> tuple[str, str, str]:
    from .candidate_identity import candidate_store_product_id
    from .product_matching_scoring import _candidate_english_name

    return (
        candidate_store_product_id(result),
        _candidate_english_name(result),
        str(result.get("productName") or ""),
    )


def _iter_results(
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> Any:
    seen: set[tuple[str, str, str]] = set()
    for query, results in search_results_by_query:
        for row_index, result in enumerate(results):
            key = _candidate_dedupe_key(result)
            if key in seen:
                continue
            seen.add(key)
            yield query, row_index, result
