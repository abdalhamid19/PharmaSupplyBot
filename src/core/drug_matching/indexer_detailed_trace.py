"""Trace event generation for detailed matching."""


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
        from .indexer_detailed_helpers import _price_bonus
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


__all__ = ["TraceEventGenerator"]
