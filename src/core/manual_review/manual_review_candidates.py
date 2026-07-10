"""Manual review candidate options models and extraction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ..matching.candidate_identity import candidate_store_product_id
from ..matching_types import MatchDecision
from ..ordering.order_ai_matching import candidate_ar, candidate_name, candidate_price
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
        return asdict(self)

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
    selected = _selected_review_diagnostics(decision.diagnostics, limit)
    return [_create_option(diag) for diag in selected]
def _selected_review_diagnostics(diagnostics, limit: int) -> list:
    """Blend top-ranked diagnostics with highly similar rejected candidates."""
    out, seen = [], set()
    for diag in _high_similarity_rejections(diagnostics) + list(diagnostics):
        candidate = diag.candidate
        key = (
            candidate_store_product_id(candidate),
            candidate_name(candidate).lower(),
            candidate_ar(candidate).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(diag)
        if len(out) >= max(1, limit):
            break
    return out
def _high_similarity_rejections(diagnostics) -> list:
    """Return rejected diagnostics that are likely useful to a human reviewer."""
    high = [diag for diag in diagnostics if _is_high_similarity_rejection(diag)]
    return sorted(high, key=lambda diag: _similarity_key(diag.breakdown), reverse=True)
def _is_high_similarity_rejection(diag) -> bool:
    breakdown = getattr(diag, "breakdown", None)
    return bool(
        breakdown and not diag.accepted and (
            breakdown.overlap_score >= 0.85
            or breakdown.sequence_score >= 0.92
            or breakdown.exact_bonus > 0.0
        )
    )
def _similarity_key(b) -> tuple:
    return (b.overlap_score, b.sequence_score, b.exact_bonus, b.numeric_overlap)
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
