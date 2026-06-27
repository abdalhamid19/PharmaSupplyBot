"""Detailed matching logic with trace generation."""

from .config import MatchingConfig
from .normalizer import DrugComponents, components_match, parse_drug
from .indexer_detailed_helpers import _parse_price, _display_score
from .indexer_detailed_lookup import LookupEngine
from .indexer_detailed_scoring import ScoringEngine
from .indexer_detailed_trace import TraceEventGenerator


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
        from .indexer_detailed_scoring import _FUZZY_SCORERS
        from .indexer_detailed_helpers import _display_score
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


__all__ = ["DetailedMatcher"]
