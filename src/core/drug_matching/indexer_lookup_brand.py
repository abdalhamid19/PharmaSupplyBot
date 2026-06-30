"""Brand-based lookup engine for DrugIndex."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from .config import MatchingConfig
from .indexer_detailed_lookup import _parse_price, _price_bonus
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
        query_price = _parse_price(query_price)
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
                        score += _price_bonus(query_price, idx, self._prices)
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


__all__ = ["BrandLookup"]
