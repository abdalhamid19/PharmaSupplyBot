"""Lookup engines for DrugIndex - brand, component, fuzzy, and best match."""

from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from .config import MatchingConfig
from .normalizer import DrugComponents, OCULAR_FORMS, components_match
from .pricing import parse_price


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
        query_price = self._parse_price(query_price)
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
        if parsed.form and self._forms_match(parsed.form, candidate.form):
            score += 10
        if parsed.flavor and parsed.flavor == candidate.flavor:
            score += 8
        if parsed.dosage_nums and parsed.dosage_nums == candidate.dosage_nums:
            score += 8
        score += self._brand_lookup._price_bonus(query_price, idx)
        return score

    def _forms_match(self, left: str, right: str) -> bool:
        """Check if two forms match (including ocular forms)."""
        if left == right:
            return True
        return bool(left in OCULAR_FORMS and right in OCULAR_FORMS)

    @staticmethod
    def _parse_price(value) -> float | None:
        """Parse price value."""
        return parse_price(value)


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
        get_record_fn,
    ):
        self._brand_lookup = brand_lookup
        self._component_lookup = component_lookup
        self._fuzzy_lookup = fuzzy_lookup
        self._parsed = parsed_list
        self._cfg = cfg
        self._norms = norms
        self._get_record = get_record_fn

    def find_best_match(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str]:
        """Find best verified match. Returns (record, score, method)."""
        from .normalizer import parse_drug
        parsed = parse_drug(drug_name)
        norm = parsed.normalized
        if not norm or len(norm) < 3:
            return None, 0.0, "too_short"
        if not parsed.brand:
            return None, 0.0, "invalid_name"
        query_price = self._brand_lookup._parse_price(price)
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
        query_price = self._brand_lookup._parse_price(query_price)
        choices = self._fuzzy_lookup._fuzzy_choices(norm)
        best = self._best_fuzzy_over(parsed, norm, query_price, choices or self._norms)
        if best is None and choices is not None:
            best = self._best_fuzzy_over(parsed, norm, query_price, self._norms)
        if best:
            return best[0], self._display_score(best[1]), best[2]
        return None, 0.0, ""

    def _best_fuzzy_over(self, parsed, norm, query_price, choices):
        """Find best fuzzy match over all scorers."""
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
            score += self._brand_lookup._price_bonus(query_price, idx)
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
