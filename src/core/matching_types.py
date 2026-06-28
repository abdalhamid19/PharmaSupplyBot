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
    critical_penalty: float
    extra_token_penalty: float
    semantic_penalty: float
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


# Token tables used by Tawreed product-matching lexical penalties
ALIAS_TO_CANONICAL = {
    "AMP": "AMPOULE",
    "AMPS": "AMPOULE",
    "BAG": "BAGS",
    "CAP": "CAPSULE",
    "CAPS": "CAPSULE",
    "CAPSULES": "CAPSULE",
    "DROP": "DROPS",
    "DRP": "DROPS",
    "FILT": "FILTER",
    "FILTERS": "FILTER",
    "FRUIT": "FRUITS",
    "INJ": "INJECTION",
    "SYP": "SYRUP",
    "SUSP": "SUSPENSION",
    "TAB": "TABLET",
    "TABS": "TABLET",
    "TABLETS": "TABLET",
    "VIT": "VITAMIN",
}
CRITICAL_TOKENS = frozenset(
    {
        "ADULT",
        "ANISE",
        "APPLE",
        "BABY",
        "BAGS",
        "CEREAL",
        "CHAMOMILE",
        "CINNAMON",
        "CLOVE",
        "CREAM",
        "DETOX",
        "DROPS",
        "EYE",
        "FILTER",
        "FORTE",
        "FRUITS",
        "GEL",
        "INJECTION",
        "JUNIOR",
        "KIDS",
        "LEMON",
        "LOTION",
        "MAX",
        "MILK",
        "MINT",
        "OINTMENT",
        "ORANGE",
        "PLUS",
        "POWDER",
        "SHAMPOO",
        "SOAP",
        "SPRAY",
        "STRAWBERRY",
        "SYRUP",
        "TABLET",
        "ULTRA",
        "VANILLA",
        "VIAL",
        "VITAMIN",
    }
)
DISTINGUISHING_TOKENS = frozenset(
    {"ADVANCED", "EXTRA", "FORTE", "MAX", "PLUS", "PRO", "SUPER", "ULTRA"}
)
CONFLICT_GROUPS = (
    frozenset({"ANISE", "CHAMOMILE", "CINNAMON", "CLOVE", "DETOX", "MINT"}),
    frozenset({"APPLE", "BANANA", "CHOCOLATE", "LEMON", "ORANGE", "STRAWBERRY"}),
    frozenset({"CREAM", "GEL", "LOTION", "OINTMENT", "SHAMPOO", "SOAP"}),
    frozenset({"DROPS", "INJECTION", "SYRUP", "VIAL"}),
)
