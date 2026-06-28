"""Manual review candidate options models and extraction."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

from .candidate_identity import candidate_store_product_id
from .matching_types import MatchDecision
from .order_ai_matching import candidate_ar, candidate_name, candidate_price


@dataclass(frozen=True)
class ReviewCandidateOption:
    """One available candidate choice for a manual review."""

    store_product_id: str
    name_en: str
    name_ar: str
    supplier: str
    available_quantity: int
    price: float
    score: float
    rejection_reason: str
    orderable: bool

    def to_dict(self) -> dict[str, Any]:
        """Return dict representation."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewCandidateOption:
        """Create from dict representation."""
        return cls(**data)


def review_candidate_options(
    decision: MatchDecision, limit: int = 5
) -> list[ReviewCandidateOption]:
    """Extract top N review options from match diagnostics."""
    if not decision or not decision.diagnostics:
        return []
    return [_create_option(diag) for diag in decision.diagnostics[:limit]]


def _create_option(diag) -> ReviewCandidateOption:
    c = diag.candidate
    store_id = candidate_store_product_id(c)
    return ReviewCandidateOption(
        store_product_id=store_id,
        name_en=candidate_name(c),
        name_ar=candidate_ar(c),
        supplier=str(c.get("storeName", "")),
        available_quantity=_parse_int(c.get("availableQuantity", 0)),
        price=_parse_float(candidate_price(c) or c.get("salePrice", 0.0)),
        score=float(diag.score),
        rejection_reason=diag.rejection_reason,
        orderable=bool(store_id),
    )


def _parse_int(val: Any) -> int:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _parse_float(val: Any) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
