"""Fuzzy lookup engine for DrugIndex."""

from __future__ import annotations

from rapidfuzz import fuzz, process

from ..config import MatchingConfig


class FuzzyLookup:
    """Handles fuzzy search operations."""

    def __init__(self, prefix_index, cfg: MatchingConfig, norms):
        self._prefix_index = prefix_index
        self._cfg = cfg
        self._norms = norms

    def lookup(self, query: str, limit: int) -> list[tuple[int, float]]:
        """Fuzzy lookup with prefix-based optimization."""
        choices = self._fuzzy_choices(query)
        hits = self._fuzzy_extract(query, limit, choices or self._norms)
        if not hits and choices is not None:
            hits = self._fuzzy_extract(query, limit, self._norms)
        return hits

    def _fuzzy_choices(self, query: str) -> dict[int, str] | None:
        """Get fuzzy choices based on prefix index."""
        subset = self._prefix_index.get(query[: self._cfg.fuzzy_prefix_len], [])
        if not subset:
            return None
        return {i: self._norms[i] for i in subset}

    def _fuzzy_extract(self, query, limit, choices) -> list[tuple[int, float]]:
        """Extract fuzzy matches using rapidfuzz."""
        results = process.extract(
            query,
            choices,
            scorer=fuzz.token_set_ratio,
            limit=limit,
        )
        return [
            (idx, score)
            for _, score, idx in results
            if score >= self._cfg.fuzzy_threshold
        ]


_FUZZY_SCORERS = (
    fuzz.token_set_ratio,
    fuzz.token_sort_ratio,
    fuzz.partial_token_sort_ratio,
)


__all__ = ["FuzzyLookup", "_FUZZY_SCORERS"]
