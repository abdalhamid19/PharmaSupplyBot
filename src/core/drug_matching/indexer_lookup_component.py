"""Component-based lookup engine for DrugIndex."""

from __future__ import annotations

from rapidfuzz import fuzz

from .config import MatchingConfig
from .indexer_detailed_lookup import _forms_match, _parse_price, _price_bonus
from .indexer_lookup_brand import BrandLookup
from .normalizer import DrugComponents, components_match


class ComponentLookup:
    """Handles component-based search operations."""

    def __init__(self, component_index, parsed_list, cfg: MatchingConfig, norms, prices):
        self._component_index = component_index
        self._parsed = parsed_list
        self._cfg = cfg
        self._norms = norms
        self._prices = prices
        self._brand_lookup = BrandLookup(None, parsed_list, cfg, norms, prices)

    def lookup(self, parsed: DrugComponents, query_price=None) -> list[tuple[int, float]]:
        """Component-based lookup."""
        query_price = _parse_price(query_price)
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
        brands = self._brand_lookup._brand_keys(parsed)
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

    def _component_score(
        self,
        parsed,
        candidate,
        idx: int,
        query_price=None,
    ) -> float:
        """Calculate component-based score."""
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
        score += _price_bonus(query_price, idx, self._prices)
        return score


__all__ = ["ComponentLookup"]
