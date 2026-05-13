"""Inverted index for fast brand-based lookup + fuzzy matching."""
import re
from collections import defaultdict

import pandas as pd
from rapidfuzz import fuzz, process

from .pricing import parse_price
from .normalizer import (
    normalize, parse_drug, DrugComponents, components_match,
    OCULAR_FORMS,
)
from .config import MatchingConfig


class DrugIndex:
    """Pre-built index over tawreed products for O(1) brand
    lookup + cached fuzzy search. Uses list-based storage."""

    __slots__ = (
        "_names_en", "_names_ar", "_ids",
        "_norms", "_parsed", "_prices",
        "_brand_index", "_component_index", "_cfg",
    )

    def __init__(self, tawreed_df: pd.DataFrame, cfg: MatchingConfig | None = None):
        self._cfg = cfg or MatchingConfig()
        original_cols = list(tawreed_df.columns)
        df = tawreed_df.rename(columns={
            original_cols[0]: "product_name_ar",
            original_cols[1]: "product_name_en",
            original_cols[2]: "store_product_id",
        })
        price_col = self._find_price_col(df, original_cols)
        self._names_en = df["product_name_en"].tolist()
        self._names_ar = df["product_name_ar"].tolist()
        self._ids = df["store_product_id"].astype(str).tolist()
        self._prices = (
            [self._parse_price(v) for v in df[price_col].tolist()]
            if price_col else [None] * len(df)
        )
        self._norms = [normalize(n) for n in self._names_en]
        self._parsed = [parse_drug(n) for n in self._names_en]
        self._brand_index: dict[str, list[int]] = defaultdict(list)
        self._component_index: dict[tuple, list[int]] = defaultdict(list)
        self._build_brand_index()
        self._build_component_index()

    def _build_brand_index(self):
        for i, parsed in enumerate(self._parsed):
            for brand in self._brand_keys(parsed):
                for plen in range(3, min(len(brand) + 1, 8)):
                    self._brand_index[brand[:plen]].append(i)

    def _build_component_index(self):
        for i, parsed in enumerate(self._parsed):
            for key in self._component_keys(parsed):
                self._component_index[key].append(i)

    # --- public read interface ---

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
        self, parsed: DrugComponents, limit: int = 10, price=None,
    ) -> list[tuple[int, float]]:
        """Return (idx, score) pairs for brand + fuzzy candidates."""
        query_price = self._parse_price(price)
        brand_hits = self._brand_lookup(parsed, query_price)
        component_hits = self._component_lookup(parsed, query_price)
        fuzzy_hits = self._fuzzy_lookup(parsed.normalized, limit)
        return self._dedupe(component_hits + brand_hits + fuzzy_hits)

    # --- internal lookups ---

    def _brand_lookup(
        self, parsed: DrugComponents, query_price=None,
    ) -> list[tuple[int, float]]:
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
                        parsed, self._parsed[idx],
                        self._cfg.brand_prefix_min,
                    )
                    if is_ok:
                        score = fuzz.token_sort_ratio(
                            parsed.normalized, self._norms[idx],
                        )
                        score += self._price_bonus(query_price, idx)
                        hits.append((idx, score))
        return hits

    @staticmethod
    def _brand_keys(parsed: DrugComponents) -> tuple[str, ...]:
        keys = []
        for brand in (parsed.brand, *parsed.brand_variants):
            cleaned = re.sub(r"[^A-Z0-9]", "", brand)
            if len(cleaned) >= 3 and cleaned not in keys:
                keys.append(cleaned)
        return tuple(keys)

    def _component_keys(self, parsed: DrugComponents) -> list[tuple]:
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

    def _component_lookup(
        self, parsed: DrugComponents, query_price=None,
    ) -> list[tuple[int, float]]:
        query_price = self._parse_price(query_price)
        hits = []
        seen = set()
        for key in self._component_keys(parsed):
            for idx in self._component_index.get(key, []):
                if idx in seen:
                    continue
                seen.add(idx)
                is_ok, _ = components_match(
                    parsed, self._parsed[idx],
                    self._cfg.brand_prefix_min,
                )
                if is_ok:
                    hits.append((
                        idx,
                        self._component_score(
                            parsed, self._parsed[idx], idx, query_price,
                        ),
                    ))
        return hits

    def _component_score(
        self, parsed, candidate, idx: int, query_price=None,
    ) -> float:
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
        score += self._price_bonus(query_price, idx)
        return score

    def _forms_match(self, left: str, right: str) -> bool:
        if left == right:
            return True
        return bool(left in OCULAR_FORMS and right in OCULAR_FORMS)

    def _fuzzy_lookup(self, query: str, limit: int) -> list[tuple[int, float]]:
        results = process.extract(
            query, self._norms,
            scorer=fuzz.token_set_ratio, limit=limit,
        )
        return [
            (idx, score) for _, score, idx in results
            if score >= self._cfg.fuzzy_threshold
        ]

    def _dedupe(self, hits: list[tuple[int, float]]) -> list[tuple[int, float]]:
        seen = set()
        out = []
        for idx, score in hits:
            if idx not in seen:
                seen.add(idx)
                out.append((idx, score))
        return out

    @staticmethod
    def _find_price_col(df: pd.DataFrame, original_cols: list[str]):
        for col in df.columns:
            if str(col).strip().lower() in {
                "price", "product_price", "selling_price", "sale_price", "سعر",
            }:
                return col
        if len(original_cols) >= 5:
            return original_cols[4]
        return None

    @staticmethod
    def _parse_price(value) -> float | None:
        return parse_price(value)

    def _price_bonus(self, query_price, idx: int) -> float:
        query_price = self._parse_price(query_price)
        candidate_price = self._prices[idx]
        if query_price is None or candidate_price is None:
            return 0.0
        diff_ratio = abs(query_price - candidate_price) / max(
            query_price, candidate_price,
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

    @staticmethod
    def _display_score(score: float) -> float:
        return min(score, 100.0)

    # --- top-level match ---

    def lookup_by_brand(self, drug_components: DrugComponents):
        """Brand lookup returning (record_dict, index) pairs."""
        return [(self.get_record(i), i) for i, _ in self._brand_lookup(drug_components)]

    def fuzzy_match(self, query: str, top_k: int | None = None):
        """Fuzzy match returning (record_dict, score, index)."""
        top_k = top_k or self._cfg.top_k_candidates
        out = []
        for idx, score in self._fuzzy_lookup(query, top_k):
            out.append((self.get_record(idx), score, idx))
        return out

    def best_match(
        self, drug_name: str, price=None,
    ) -> tuple[dict | None, float, str]:
        """Find best verified match. Returns (record, score, method)."""
        parsed = parse_drug(drug_name)
        norm = parsed.normalized
        if not norm or len(norm) < 3:
            return None, 0.0, "too_short"
        if not parsed.brand:
            return None, 0.0, "invalid_name"
        query_price = self._parse_price(price)
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

    def best_match_detailed(
        self, drug_name: str, price=None,
    ) -> tuple[dict | None, float, str, dict]:
        """Like best_match but also returns trace dict for logging."""
        parsed = parse_drug(drug_name)
        norm = parsed.normalized
        query_price = self._parse_price(price)
        trace = {
            "norm": norm, "brand": parsed.brand,
            "brand_hits": [], "fuzzy_steps": [],
            "component_checks": [], "candidates": [],
            "score_breakdowns": [],
        }
        if not norm or len(norm) < 3:
            return None, 0.0, "too_short", trace
        if not parsed.brand:
            return None, 0.0, "invalid_name", trace
        component_hits = self._component_lookup(parsed, query_price)
        trace["candidates"].extend(
            self._candidate_events("component_index", component_hits),
        )
        trace["score_breakdowns"].extend(
            self._score_events("component_index", component_hits, query_price),
        )
        if component_hits:
            best_idx, best_score = max(component_hits, key=lambda x: x[1])
            if best_score >= self._cfg.fuzzy_threshold:
                ok, reason = components_match(
                    parsed, self._parsed[best_idx],
                    self._cfg.brand_prefix_min,
                )
                trace["component_checks"].append((best_idx, ok, reason))
                if ok:
                    return (
                        self.get_record(best_idx),
                        self._display_score(best_score),
                        "component_index", trace,
                    )
        hits = self._brand_lookup(parsed, query_price)
        trace["brand_hits"] = hits
        trace["candidates"].extend(self._candidate_events("brand_index", hits))
        trace["score_breakdowns"].extend(
            self._score_events("brand_index", hits, query_price),
        )
        if hits:
            best_idx, best_score = max(hits, key=lambda x: x[1])
            if best_score >= self._cfg.fuzzy_threshold:
                ok, reason = components_match(
                    parsed, self._parsed[best_idx],
                    self._cfg.brand_prefix_min,
                )
                trace["component_checks"].append(
                    (best_idx, ok, reason),
                )
                if ok:
                    return (
                        self.get_record(best_idx),
                        self._display_score(best_score),
                        "brand_index", trace,
                    )
        for scorer in [fuzz.token_set_ratio, fuzz.token_sort_ratio, fuzz.partial_token_sort_ratio]:
            result = process.extractOne(
                norm, self._norms, scorer=scorer,
                score_cutoff=self._cfg.fuzzy_threshold,
            )
            trace["fuzzy_steps"].append(
                (scorer.__name__, result),
            )
            if result:
                _, score, idx = result
                price_bonus = self._price_bonus(query_price, idx)
                trace["candidates"].append({
                    "idx": idx, "source": scorer.__name__,
                    "rank": 1, "score": score,
                })
                trace["score_breakdowns"].append({
                    "idx": idx, "source": scorer.__name__,
                    "rank": 1, "base_score": score,
                    "price_bonus": price_bonus,
                    "final_score": score + price_bonus,
                    "threshold": self._cfg.fuzzy_threshold,
                })
                ok, reason = components_match(
                    parsed, self._parsed[idx],
                    self._cfg.brand_prefix_min,
                )
                trace["component_checks"].append(
                    (idx, ok, reason),
                )
                if ok:
                    score += price_bonus
                    return (
                        self.get_record(idx), self._display_score(score),
                        scorer.__name__, trace,
                    )
        return None, 0.0, "no_match", trace

    def _candidate_events(self, source, hits):
        return [
            {"idx": idx, "source": source, "rank": rank, "score": score}
            for rank, (idx, score) in enumerate(hits[:5], start=1)
        ]

    def _score_events(self, source, hits, query_price):
        events = []
        for rank, (idx, score) in enumerate(hits[:5], start=1):
            price_bonus = self._price_bonus(query_price, idx)
            events.append({
                "idx": idx, "source": source, "rank": rank,
                "base_score": score - price_bonus,
                "price_bonus": price_bonus,
                "final_score": score,
                "threshold": self._cfg.fuzzy_threshold,
            })
        return events

    def _try_brand_match(self, parsed, norm, query_price=None):
        hits = self._brand_lookup(parsed, query_price)
        if not hits:
            return None, 0.0
        best_idx, best_score = max(hits, key=lambda x: x[1])
        if best_score >= self._cfg.fuzzy_threshold:
            return self.get_record(best_idx), self._display_score(best_score)
        return None, 0.0

    def _try_component_match(self, parsed, query_price=None):
        hits = self._component_lookup(parsed, query_price)
        if not hits:
            return None, 0.0
        best_idx, best_score = max(hits, key=lambda x: x[1])
        if best_score >= self._cfg.fuzzy_threshold:
            return self.get_record(best_idx), self._display_score(best_score)
        return None, 0.0

    def _try_fuzzy_match(self, parsed, norm, query_price=None):
        query_price = self._parse_price(query_price)
        best = None
        for scorer in [fuzz.token_set_ratio, fuzz.token_sort_ratio, fuzz.partial_token_sort_ratio]:
            result = process.extractOne(
                norm, self._norms, scorer=scorer,
                score_cutoff=self._cfg.fuzzy_threshold,
            )
            if result:
                _, score, idx = result
                is_ok, _ = components_match(
                    parsed, self._parsed[idx],
                    self._cfg.brand_prefix_min,
                )
                score += self._price_bonus(query_price, idx)
                if is_ok and (best is None or score > best[1]):
                    best = (self.get_record(idx), score, scorer.__name__)
        if best:
            return best[0], self._display_score(best[1]), best[2]
        return None, 0.0, ""

    @property
    def size(self) -> int:
        return len(self._names_en)

    @property
    def norms(self) -> list[str]:
        """Public read-only access to normalized names list."""
        return self._norms
