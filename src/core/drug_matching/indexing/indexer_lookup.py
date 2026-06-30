"""Lookup engines for DrugIndex - brand, component, fuzzy, and best match.

This module re-exports all lookup classes from specialized submodules.
"""

from __future__ import annotations

from rapidfuzz import process

from ..config import MatchingConfig
from .indexer_lookup_brand import BrandLookup
from .indexer_lookup_component import ComponentLookup
from .indexer_lookup_fuzzy import FuzzyLookup, _FUZZY_SCORERS
from ..normalization.normalizer import DrugComponents, components_match


class BestMatchFinder:
    """Handles best match finding operations."""

    def __init__(
        self,
        brand_lookup: BrandLookup,
        component_lookup: ComponentLookup,
        fuzzy_lookup: FuzzyLookup,
        parsed_list,
        cfg: MatchingConfig,
        norms,
        prices,
        get_record_fn,
    ):
        self._brand_lookup = brand_lookup
        self._component_lookup = component_lookup
        self._fuzzy_lookup = fuzzy_lookup
        self._parsed = parsed_list
        self._cfg = cfg
        self._norms = norms
        self._prices = prices
        self._get_record = get_record_fn

    def find_best_match(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str]:
        """Find best verified match. Returns (record, score, method)."""
        from .indexer_detailed_lookup import _parse_price
        from ..normalization.normalizer import parse_drug

        parsed = parse_drug(drug_name)
        norm = parsed.normalized
        if not norm or len(norm) < 3:
            return None, 0.0, "too_short"
        if not parsed.brand:
            return None, 0.0, "invalid_name"
        query_price = _parse_price(price)
        rec, score = self._try_component_match(parsed, query_price)
        if rec is not None:
            return rec, score, "component_index"
        rec, score = self._try_brand_match(parsed, norm, query_price)
        if rec is not None:
            return rec, score, "brand_index"
        rec, score, method = self._try_fuzzy_match(parsed, norm, query_price)
        if rec is not None:
            return rec, score, method
        return None, 0.0, "no_match"

    def _try_brand_match(self, parsed, norm, query_price=None):
        """Try brand-based match."""
        hits = self._brand_lookup.lookup(parsed, query_price)
        if not hits:
            return None, 0.0
        best_idx, best_score = max(hits, key=lambda x: x[1])
        if best_score >= self._cfg.fuzzy_threshold:
            return self._get_record(best_idx), self._display_score(best_score)
        return None, 0.0

    def _try_component_match(self, parsed, query_price=None):
        """Try component-based match."""
        hits = self._component_lookup.lookup(parsed, query_price)
        if not hits:
            return None, 0.0
        best_idx, best_score = max(hits, key=lambda x: x[1])
        if best_score >= self._cfg.fuzzy_threshold:
            return self._get_record(best_idx), self._display_score(best_score)
        return None, 0.0

    def _try_fuzzy_match(self, parsed, norm, query_price=None):
        """Try fuzzy-based match."""
        from .indexer_detailed_lookup import _parse_price

        query_price = _parse_price(query_price)
        choices = self._fuzzy_lookup._fuzzy_choices(norm)
        best = self._best_fuzzy_over(parsed, norm, query_price, choices or self._norms)
        if best is None and choices is not None:
            best = self._best_fuzzy_over(parsed, norm, query_price, self._norms)
        if best:
            return best[0], self._display_score(best[1]), best[2]
        return None, 0.0, ""

    def _best_fuzzy_over(self, parsed, norm, query_price, choices):
        """Find best fuzzy match over all scorers."""
        from .indexer_detailed_lookup import _price_bonus

        best = None
        for scorer in _FUZZY_SCORERS:
            result = process.extractOne(
                norm,
                choices,
                scorer=scorer,
                score_cutoff=self._cfg.fuzzy_threshold,
            )
            if not result:
                continue
            _, score, idx = result
            is_ok, _ = components_match(
                parsed, self._parsed[idx], self._cfg.brand_prefix_min
            )
            score += _price_bonus(query_price, self._prices[idx])
            if is_ok and (best is None or score > best[1]):
                best = (self._get_record(idx), score, scorer.__name__)
        return best

    @staticmethod
    def _display_score(score: float) -> float:
        """Display score capped at 100."""
        return min(score, 100.0)


class LookupEngine:
    """Wrapper for all lookup engines."""

    def __init__(
        self,
        norms,
        parsed,
        prices,
        brand_index,
        component_index,
        prefix_index,
        cfg,
    ):
        self._brand_lookup = BrandLookup(
            brand_index, parsed, cfg, norms, prices
        )
        self._component_lookup = ComponentLookup(
            component_index, parsed, cfg, norms, prices
        )
        self._fuzzy_lookup = FuzzyLookup(prefix_index, cfg, norms)
        self._norms = norms
        self._parsed = parsed
        self._prices = prices
        self._cfg = cfg

    def component_lookup(self, parsed, query_price):
        """Component lookup."""
        return self._component_lookup.lookup(parsed, query_price)

    def brand_lookup(self, parsed, query_price):
        """Brand lookup."""
        return self._brand_lookup.lookup(parsed, query_price)

    def fuzzy_choices(self, norm):
        """Get fuzzy choices."""
        return self._fuzzy_lookup._fuzzy_choices(norm)


__all__ = [
    "BrandLookup",
    "ComponentLookup",
    "FuzzyLookup",
    "BestMatchFinder",
    "LookupEngine",
    "_FUZZY_SCORERS",
]
