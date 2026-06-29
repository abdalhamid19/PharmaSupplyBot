"""Trace event generation for detailed matching."""

from __future__ import annotations


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


__all__ = [
    "TraceEventGenerator",
]
