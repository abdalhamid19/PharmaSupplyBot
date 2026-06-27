"""Lookup functions for detailed matching."""

import re
from rapidfuzz import fuzz, process

from .config import MatchingConfig
from .normalizer import DrugComponents, components_match


class LookupEngine:
    """Handles component, brand, and fuzzy lookups."""

    def __init__(
        self,
        norms: list,
        parsed: list,
        prices: list,
        brand_index: dict,
        component_index: dict,
        prefix_index: dict,
        cfg: MatchingConfig | None = None,
    ):
        self._norms = norms
        self._parsed = parsed
        self._prices = prices
        self._brand_index = brand_index
        self._component_index = component_index
        self._prefix_index = prefix_index
        self._cfg = cfg or MatchingConfig()

    def component_lookup(
        self,
        parsed: DrugComponents,
        query_price=None,
    ) -> list[tuple[int, float]]:
        """Component-based lookup."""
        hits = []
        seen = set()
        for key in self._component_keys(parsed):
            for idx in self._component_index.get(key, []):
                if idx in seen:
                    continue
                seen.add(idx)
                is_ok, _ = components_match(
                    parsed,
                    self._parsed[idx],
                    self._cfg.brand_prefix_min,
                )
                if is_ok:
                    hits.append(
                        (
                            idx,
                            self._component_score(
                                parsed,
                                self._parsed[idx],
                                idx,
                                query_price,
                            ),
                        )
                    )
        return hits

    def _component_keys(self, parsed: DrugComponents) -> list[tuple]:
        """Extract component keys for lookup."""
        brands = self._brand_keys(parsed)
        if not brands:
            return []
        keys = []
        for brand in brands:
            keys.append(("brand", brand))
            if parsed.volume:
                keys.append(("brand_volume", brand, parsed.volume))
            if parsed.qty:
                keys.append(("brand_qty", brand, parsed.qty))
            if parsed.dosage_nums:
                keys.append(("brand_dosage", brand, parsed.dosage_nums))
            if parsed.flavor:
                keys.append(("brand_flavor", brand, parsed.flavor))
        return keys

    @staticmethod
    def _brand_keys(parsed: DrugComponents) -> tuple[str, ...]:
        """Extract brand keys from parsed components."""
        keys = []
        for brand in (parsed.brand, *parsed.brand_variants):
            cleaned = re.sub(r"[^A-Z0-9]", "", brand)
            if len(cleaned) >= 3 and cleaned not in keys:
                keys.append(cleaned)
        return tuple(keys)

    def _component_score(
        self,
        parsed,
        candidate,
        idx: int,
        query_price=None,
    ) -> float:
        """Calculate component-based score."""
        from .indexer_detailed_helpers import _forms_match, _price_bonus
        score = fuzz.token_set_ratio(parsed.normalized, self._norms[idx])
        if parsed.volume and parsed.volume == candidate.volume:
            score += 10
        if parsed.qty and parsed.qty == candidate.qty:
            score += 8
        if parsed.form and _forms_match(parsed.form, candidate.form):
            score += 10
        if parsed.flavor and parsed.flavor == candidate.flavor:
            score += 8
        if parsed.dosage_nums and parsed.dosage_nums == candidate.dosage_nums:
            score += 8
        score += _price_bonus(query_price, self._prices[idx])
        return score

    def brand_lookup(
        self,
        parsed: DrugComponents,
        query_price=None,
    ) -> list[tuple[int, float]]:
        """Brand-based lookup."""
        brands = self._brand_keys(parsed)
        if not brands:
            return []
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
                        from .indexer_detailed_helpers import _price_bonus
                        score += _price_bonus(query_price, self._prices[idx])
                        hits.append((idx, score))
        return hits

    def fuzzy_choices(self, query: str) -> dict[int, str] | None:
        """Get fuzzy choices based on prefix index."""
        subset = self._prefix_index.get(query[: self._cfg.fuzzy_prefix_len], [])
        if not subset:
            return None
        return {i: self._norms[i] for i in subset}


__all__ = ["LookupEngine"]
