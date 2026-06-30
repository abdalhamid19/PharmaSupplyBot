"""Inverted index for fast brand-based lookup + fuzzy matching."""

from ..config import MatchingConfig
from .indexer_build import IndexBuilder
from .indexer_search import IndexSearcher
from .indexer_detailed import DetailedMatcher


class DrugIndex:
    """Pre-built index over tawreed products for O(1) brand
    lookup + cached fuzzy search. Uses list-based storage."""

    __slots__ = (
        "_searcher",
        "_detailed",
    )

    def __init__(self, tawreed_df, cfg: MatchingConfig | None = None):
        builder = IndexBuilder(tawreed_df, cfg)
        indexes = builder.get_indexes()
        self._searcher = IndexSearcher(*indexes, cfg)
        self._detailed = DetailedMatcher(*indexes, cfg)

    # --- public read interface ---

    def get_record(self, idx: int) -> dict:
        """Return record dict for a given index."""
        return self._searcher.get_record(idx)

    def get_parsed(self, idx):
        """Return parsed components for a given index."""
        return self._searcher.get_parsed(idx)

    def score_candidate(self, query_norm: str, idx: int, scorer=None) -> float:
        """Score a candidate by index using the given scorer."""
        return self._searcher.score_candidate(query_norm, idx, scorer)

    def get_candidates(
        self,
        parsed,
        limit: int = 10,
        price=None,
    ) -> list[tuple[int, float]]:
        """Return (idx, score) pairs for brand + fuzzy candidates."""
        return self._searcher.get_candidates(parsed, limit, price)

    # --- top-level match ---

    def lookup_by_brand(self, drug_components):
        """Brand lookup returning (record_dict, index) pairs."""
        return self._searcher.lookup_by_brand(drug_components)

    def fuzzy_match(self, query: str, top_k: int | None = None):
        """Fuzzy match returning (record_dict, score, index)."""
        return self._searcher.fuzzy_match(query, top_k)

    def best_match(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str]:
        """Find best verified match. Returns (record, score, method)."""
        return self._searcher.best_match(drug_name, price)

    def best_match_detailed(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str, dict]:
        """Like best_match but also returns trace dict for logging."""
        return self._detailed.best_match_detailed(drug_name, price)

    @property
    def size(self) -> int:
        """Return the number of products in the index."""
        return len(self._searcher._names_en)

    @property
    def norms(self) -> list[str]:
        """Public read-only access to normalized names list."""
        return self._searcher._norms


__all__ = ["DrugIndex"]
