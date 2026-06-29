"""Search logic for DrugIndex."""

from rapidfuzz import fuzz

from .config import MatchingConfig
from .normalizer import DrugComponents
from .indexer_lookup import (
    BrandLookup,
    ComponentLookup,
    FuzzyLookup,
    BestMatchFinder,
)


class IndexSearcher:
    """Handles search operations for DrugIndex."""

    def __init__(
        self,
        names_en: list,
        names_ar: list,
        ids: list,
        norms: list,
        parsed: list,
        prices: list,
        brand_index: dict,
        component_index: dict,
        prefix_index: dict,
        cfg: MatchingConfig | None = None,
    ):
        self._names_en = names_en
        self._names_ar = names_ar
        self._ids = ids
        self._norms = norms
        self._parsed = parsed
        self._prices = prices
        self._cfg = cfg or MatchingConfig()
        self._init_lookups(brand_index, component_index, prefix_index)

    def _init_lookups(self, brand_index, component_index, prefix_index):
        """Initialize lookup objects."""
        self._brand_lookup = BrandLookup(
            brand_index, self._parsed, self._cfg, self._norms, self._prices
        )
        self._component_lookup = ComponentLookup(
            component_index, self._parsed, self._cfg, self._norms, self._prices
        )
        self._fuzzy_lookup = FuzzyLookup(prefix_index, self._cfg, self._norms)
        self._best_match_finder = BestMatchFinder(
            self._brand_lookup,
            self._component_lookup,
            self._fuzzy_lookup,
            self._parsed,
            self._cfg,
            self._norms,
            self.get_record,
        )

    def get_record(self, idx: int) -> dict:
        """Return record dict for a given index."""
        return {
            "product_name_en": self._names_en[idx],
            "product_name_ar": self._names_ar[idx],
            "store_product_id": self._ids[idx],
            "price": self._prices[idx],
        }

    def get_parsed(self, idx: int) -> DrugComponents:
        """Return parsed components for a given index."""
        return self._parsed[idx]

    def score_candidate(self, query_norm: str, idx: int, scorer=None) -> float:
        """Score a candidate by index using the given scorer."""
        scorer = scorer or fuzz.token_sort_ratio
        return scorer(query_norm, self._norms[idx])

    def get_candidates(
        self,
        parsed: DrugComponents,
        limit: int = 10,
        price=None,
    ) -> list[tuple[int, float]]:
        """Return (idx, score) pairs for brand + fuzzy candidates."""
        query_price = self._brand_lookup._parse_price(price)
        brand_hits = self._brand_lookup.lookup(parsed, query_price)
        component_hits = self._component_lookup.lookup(parsed, query_price)
        fuzzy_hits = self._fuzzy_lookup.lookup(parsed.normalized, limit)
        return self._dedupe(component_hits + brand_hits + fuzzy_hits)

    def _dedupe(self, hits: list[tuple[int, float]]) -> list[tuple[int, float]]:
        """Remove duplicate indices from hits."""
        seen = set()
        out = []
        for idx, score in hits:
            if idx not in seen:
                seen.add(idx)
                out.append((idx, score))
        return out

    def lookup_by_brand(self, drug_components: DrugComponents):
        """Brand lookup returning (record_dict, index) pairs."""
        return [(self.get_record(i), i) for i, _ in self._brand_lookup.lookup(drug_components)]

    def fuzzy_match(self, query: str, top_k: int | None = None):
        """Fuzzy match returning (record_dict, score, index)."""
        top_k = top_k or self._cfg.top_k_candidates
        out = []
        for idx, score in self._fuzzy_lookup.lookup(query, top_k):
            out.append((self.get_record(idx), score, idx))
        return out

    def best_match(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str]:
        """Find best verified match. Returns (record, score, method)."""
        return self._best_match_finder.find_best_match(drug_name, price)


__all__ = ["IndexSearcher"]
