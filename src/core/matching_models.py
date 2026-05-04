"""Diagnostic and result dataclasses used by Tawreed product matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SearchMatch:
    """The winning search query, row index, score, and Tawreed payload for a match."""

    query: str
    row_index: int
    score: float
    data: dict[str, Any]


@dataclass(frozen=True)
class MatchScoreBreakdown:
    """Detailed score components used when evaluating one Tawreed candidate."""

    sequence_score: float
    overlap_score: float
    numeric_overlap: float
    exact_bonus: float
    availability_bonus: float
    total_score: float


@dataclass(frozen=True)
class CandidateMatchDiagnostic:
    """Diagnostic data for one candidate considered during product matching."""

    query: str
    row_index: int
    score: float
    sort_key: tuple[float, int, float, int, int, int]
    accepted: bool
    accepted_reason: str
    rejection_reason: str
    breakdown: MatchScoreBreakdown
    candidate: dict[str, Any]


@dataclass(frozen=True)
class MatchDecision:
    """Final match decision plus diagnostics for every candidate inspected."""

    best_match: SearchMatch | None
    diagnostics: list[CandidateMatchDiagnostic]
    final_reason: str
