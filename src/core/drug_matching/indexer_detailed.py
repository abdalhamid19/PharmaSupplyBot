"""Detailed matching logic with trace generation."""

from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from .config import MatchingConfig
from .normalizer import DrugComponents, OCULAR_FORMS, components_match
from .pricing import parse_price


# Helper functions
def _parse_price(value) -> float | None:
    """Parse price value."""
    return parse_price(value)


def _price_bonus(query_price, candidate_price) -> float:
    """Calculate price-based score bonus."""
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


def _forms_match(left: str, right: str) -> bool:
    """Check if two forms match (including ocular forms)."""
    if left == right:
        return True
    return bool(left in OCULAR_FORMS and right in OCULAR_FORMS)


def _display_score(score: float) -> float:
    """Display score capped at 100."""
    return min(score, 100.0)


# Trace event generation
class TraceEventGenerator:
    """Generates trace events for detailed matching."""

    def __init__(self, cfg):
        self._cfg = cfg

    def candidate_events(self, source, hits):
        """Generate candidate events for trace."""
        return [
            {"idx": idx, "source": source, "rank": rank, "score": score}
            for rank, (idx, score) in enumerate(hits[:5], start=1)
        ]

    def score_events(self, source, hits, query_price, prices):
        """Generate score events for trace."""
        events = []
        for rank, (idx, score) in enumerate(hits[:5], start=1):
            price_bonus = _price_bonus(query_price, prices[idx])
            events.append(
                {
                    "idx": idx,
                    "source": source,
                    "rank": rank,
                    "base_score": score - price_bonus,
                    "price_bonus": price_bonus,
                    "final_score": score,
                    "threshold": self._cfg.fuzzy_threshold,
                }
            )
        return events


# Lookup engine
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
                        score += _price_bonus(query_price, self._prices[idx])
                        hits.append((idx, score))
        return hits

    def fuzzy_choices(self, query: str) -> dict[int, str] | None:
        """Get fuzzy choices based on prefix index."""
        subset = self._prefix_index.get(query[: self._cfg.fuzzy_prefix_len], [])
        if not subset:
            return None
        return {i: self._norms[i] for i in subset}


# Scoring engine
_FUZZY_SCORERS = (
    fuzz.token_set_ratio,
    fuzz.token_sort_ratio,
    fuzz.partial_token_sort_ratio,
)


class ScoringEngine:
    """Handles fuzzy scoring with trace generation."""

    def __init__(
        self,
        norms: list,
        parsed: list,
        prices: list,
        cfg: MatchingConfig | None = None,
    ):
        self._norms = norms
        self._parsed = parsed
        self._prices = prices
        self._cfg = cfg or MatchingConfig()

    def fuzzy_match(
        self,
        norm: str,
        parsed: DrugComponents,
        query_price=None,
        fuzzy_choices=None,
    ) -> tuple[int | None, float, str]:
        """Run fuzzy matching with multiple scorers."""
        for scorer in _FUZZY_SCORERS:
            result = process.extractOne(
                norm,
                fuzzy_choices or self._norms,
                scorer=scorer,
                score_cutoff=self._cfg.fuzzy_threshold,
            )
            if not result and fuzzy_choices is not None:
                result = process.extractOne(
                    norm,
                    self._norms,
                    scorer=scorer,
                    score_cutoff=self._cfg.fuzzy_threshold,
                )
            if result:
                _, score, idx = result
                price_bonus = _price_bonus(query_price, self._prices[idx])
                ok, _ = components_match(
                    parsed,
                    self._parsed[idx],
                    self._cfg.brand_prefix_min,
                )
                if ok:
                    final_score = score + price_bonus
                    return idx, _display_score(final_score), scorer.__name__
        return None, 0.0, "no_match"

    def single_scorer_match(
        self,
        norm: str,
        parsed: DrugComponents,
        query_price=None,
        fuzzy_choices=None,
        scorer=None,
    ) -> tuple[int | None, float, str]:
        """Run single scorer fuzzy matching."""
        result = process.extractOne(
            norm,
            fuzzy_choices or self._norms,
            scorer=scorer,
            score_cutoff=self._cfg.fuzzy_threshold,
        )
        if not result and fuzzy_choices is not None:
            result = process.extractOne(
                norm,
                self._norms,
                scorer=scorer,
                score_cutoff=self._cfg.fuzzy_threshold,
            )
        if result:
            _, score, idx = result
            price_bonus = _price_bonus(query_price, self._prices[idx])
            ok, _ = components_match(
                parsed,
                self._parsed[idx],
                self._cfg.brand_prefix_min,
            )
            if ok:
                final_score = score + price_bonus
                return idx, _display_score(final_score), scorer.__name__
        return None, 0.0, "no_match"


# Main detailed matcher
class DetailedMatcher:
    """Handles detailed matching with trace generation."""

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
        self._lookup = LookupEngine(norms, parsed, prices, brand_index, component_index, prefix_index, cfg)
        self._scoring = ScoringEngine(norms, parsed, prices, cfg)
        self._trace = TraceEventGenerator(cfg)

    def get_record(self, idx: int) -> dict:
        """Return record dict for a given index."""
        return {
            "product_name_en": self._names_en[idx],
            "product_name_ar": self._names_ar[idx],
            "store_product_id": self._ids[idx],
            "price": self._prices[idx],
        }

    def best_match_detailed(
        self,
        drug_name: str,
        price=None,
    ) -> tuple[dict | None, float, str, dict]:
        """Like best_match but also returns trace dict for logging."""
        from .normalizer import parse_drug
        parsed = parse_drug(drug_name)
        norm = parsed.normalized
        query_price = _parse_price(price)
        trace = {
            "norm": norm,
            "brand": parsed.brand,
            "brand_hits": [],
            "fuzzy_steps": [],
            "component_checks": [],
            "candidates": [],
            "score_breakdowns": [],
        }
        if not norm or len(norm) < 3:
            return None, 0.0, "too_short", trace
        if not parsed.brand:
            return None, 0.0, "invalid_name", trace
        
        # Component lookup
        component_hits = self._lookup.component_lookup(parsed, query_price)
        trace["candidates"].extend(
            self._trace.candidate_events("component_index", component_hits),
        )
        trace["score_breakdowns"].extend(
            self._trace.score_events("component_index", component_hits, query_price, self._prices),
        )
        if component_hits:
            best_idx, best_score = max(component_hits, key=lambda x: x[1])
            if best_score >= self._cfg.fuzzy_threshold:
                ok, reason = components_match(
                    parsed,
                    self._parsed[best_idx],
                    self._cfg.brand_prefix_min,
                )
                trace["component_checks"].append((best_idx, ok, reason))
                if ok:
                    return (
                        self.get_record(best_idx),
                        _display_score(best_score),
                        "component_index",
                        trace,
                    )
        
        # Brand lookup
        hits = self._lookup.brand_lookup(parsed, query_price)
        trace["brand_hits"] = hits
        trace["candidates"].extend(self._trace.candidate_events("brand_index", hits))
        trace["score_breakdowns"].extend(
            self._trace.score_events("brand_index", hits, query_price, self._prices),
        )
        if hits:
            best_idx, best_score = max(hits, key=lambda x: x[1])
            if best_score >= self._cfg.fuzzy_threshold:
                ok, reason = components_match(
                    parsed,
                    self._parsed[best_idx],
                    self._cfg.brand_prefix_min,
                )
                trace["component_checks"].append(
                    (best_idx, ok, reason),
                )
                if ok:
                    return (
                        self.get_record(best_idx),
                        _display_score(best_score),
                        "brand_index",
                        trace,
                    )
        
        # Fuzzy matching
        fuzzy_choices = self._lookup.fuzzy_choices(norm)
        for scorer in _FUZZY_SCORERS:
            result = self._scoring.single_scorer_match(norm, parsed, query_price, fuzzy_choices, scorer)
            if result[0] is not None:
                idx, score, method = result
                trace["fuzzy_steps"].append((scorer.__name__, (norm, score, idx)))
                trace["candidates"].append(
                    {"idx": idx, "source": method, "rank": 1, "score": score}
                )
                return (
                    self.get_record(idx),
                    score,
                    method,
                    trace,
                )
            trace["fuzzy_steps"].append((scorer.__name__, None))
        
        return None, 0.0, "no_match", trace


__all__ = [
    "DetailedMatcher",
    "LookupEngine",
    "ScoringEngine",
    "TraceEventGenerator",
    "_FUZZY_SCORERS",
    "_parse_price",
    "_price_bonus",
    "_forms_match",
    "_display_score",
]
