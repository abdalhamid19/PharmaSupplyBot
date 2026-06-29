"""Scoring engine for detailed matching."""

from __future__ import annotations

from rapidfuzz import fuzz, process

from .config import MatchingConfig
from .normalizer import DrugComponents, components_match
from .pricing import parse_price


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


def _display_score(score: float) -> float:
    """Display score capped at 100."""
    return min(score, 100.0)


__all__ = [
    "_FUZZY_SCORERS",
    "ScoringEngine",
    "_display_score",
]
