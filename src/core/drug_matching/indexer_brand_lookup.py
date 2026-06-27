"""Brand-based lookup logic for IndexSearcher."""

import re

from rapidfuzz import fuzz

from .config import MatchingConfig
from .normalizer import DrugComponents, components_match


class BrandLookup:
    """Handles brand-based search operations."""

    def __init__(self, brand_index, parsed_list, cfg: MatchingConfig, norms, prices):
        self._brand_index = brand_index
        self._parsed = parsed_list
        self._cfg = cfg
        self._norms = norms
        self._prices = prices

    def lookup(self, parsed: DrugComponents, query_price=None) -> list[tuple[int, float]]:
        """Brand-based lookup."""
        brands = self._brand_keys(parsed)
        if not brands:
            return []
        query_price = self._parse_price(query_price)
        hits = []
        seen = set()
        for brand in brands:
            for plen in range(min(len(brand), 7), 2, -1):
                for idx in self._brand_index.get(brand[:plen], []):
                    if idx in seen:
                        continue
                    seen.add(idx)
                    is_ok, _ = components_match(
                        parsed,
                        self._parsed[idx],
                        self._cfg.brand_prefix_min,
                    )
                    if is_ok:
                        score = fuzz.token_sort_ratio(
                            parsed.normalized,
                            self._norms[idx],
                        )
                        score += self._price_bonus(query_price, idx)
                        hits.append((idx, score))
        return hits

    @staticmethod
    def _brand_keys(parsed: DrugComponents) -> tuple[str, ...]:
        """Extract brand keys from parsed components."""
        keys = []
        for brand in (parsed.brand, *parsed.brand_variants):
            cleaned = re.sub(r"[^A-Z0-9]", "", brand)
            if len(cleaned) >= 3 and cleaned not in keys:
                keys.append(cleaned)
        return tuple(keys)

    @staticmethod
    def _parse_price(value) -> float | None:
        """Parse price value."""
        from .pricing import parse_price
        return parse_price(value)

    def _price_bonus(self, query_price, idx: int) -> float:
        """Calculate price-based score bonus."""
        query_price = self._parse_price(query_price)
        candidate_price = self._prices[idx]
        if query_price is None or candidate_price is None:
            return 0.0
        diff_ratio = abs(query_price - candidate_price) / max(
            query_price,
            candidate_price,
        )
        if diff_ratio == 0:
            return 6.0
        if diff_ratio <= 0.02:
            return 5.0
        if diff_ratio <= 0.05:
            return 4.0
        if diff_ratio <= 0.10:
            return 2.0
        return 0.0
