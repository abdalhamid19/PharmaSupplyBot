"""Candidate-source selection for Tawreed product search."""
from __future__ import annotations

from typing import Any

from ..core.candidate_identity import candidate_has_store_product_id


def select_search_candidates(
    api_candidates: list[dict[str, Any]] | None,
    dom_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return API candidates unless DOM is needed for orderable ids."""
    if api_candidates is None:
        return dom_candidates
    if not api_candidates or has_orderable_candidate(api_candidates):
        return api_candidates
    return dom_candidates or api_candidates


def has_orderable_candidate(candidates: list[dict[str, Any]]) -> bool:
    """Return whether any candidate can be used for ordering."""
    return any(candidate_has_store_product_id(candidate) for candidate in candidates)


__all__ = ["select_search_candidates", "has_orderable_candidate"]
