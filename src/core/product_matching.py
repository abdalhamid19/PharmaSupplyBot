"""Product matching facade - re-exports from specialized modules."""

from __future__ import annotations

from typing import Any

from .config.config_models import MatchingConfig
from .matching_types import MatchDecision, SearchMatch
from .utils.excel import Item

# Import from specialized modules
from .product_matching_decisions import (
    _build_candidate_diagnostics,
    _decision_from_diagnostics,
)
from .product_matching_scoring import (
    _candidate_texts,
    _normalize_text,
)
from .product_matching_queries import (
    search_queries_for_item as _search_queries_for_item,
)
from .product_matching_queries import (
    search_queries_for_item as _search_queries_for_item,
)


# Public API functions


def find_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> SearchMatch | None:
    """Return the highest-ranked acceptable search result across all generated queries."""
    return explain_best_product_match(
        item, search_results_by_query, matching_config
    ).best_match


def explain_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> MatchDecision:
    """Return the best match plus diagnostics for every candidate considered."""
    from .matching_rules import default_matching_config

    active_matching_config = matching_config or default_matching_config()
    diagnostics = _build_candidate_diagnostics(
        item,
        search_results_by_query,
        active_matching_config,
    )
    return _decision_from_diagnostics(diagnostics)


def is_decisive_product_match(query: str, candidate: dict[str, Any]) -> bool:
    """Return whether the candidate is an exact normalized name match for the query."""
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return False
    return normalized_query in _candidate_texts(candidate)
