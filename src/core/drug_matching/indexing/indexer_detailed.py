"""Detailed matching logic with trace generation - re-exports from split modules."""

from __future__ import annotations

# Re-export from split modules
from .indexer_detailed_best_match import DetailedMatcher
from .indexer_detailed_lookup import (
    _forms_match,
    _parse_price,
    _price_bonus,
)
from .indexer_detailed_scoring import (
    _FUZZY_SCORERS,
    _display_score,
    ScoringEngine,
)
from .indexer_lookup import LookupEngine
from .indexer_trace import TraceEventGenerator


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
