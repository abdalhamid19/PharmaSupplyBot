"""Manual review candidate options models and extraction."""

from __future__ import annotations

import dataclasses
from dataclasses import asdict, dataclass
from typing import Any

from ..matching.candidate_identity import candidate_store_product_id
from ..matching_types import MatchDecision
from .candidate_limits import normalize_candidate_limit


def candidate_name(candidate: dict) -> str:
    return str(candidate.get("productNameEn") or candidate.get("productNameEnFallback") or candidate.get("productName") or "")


def candidate_ar(candidate: dict) -> str:
    return str(candidate.get("productName") or "")


def candidate_price(candidate: dict) -> object:
    return candidate.get("retailPrice") or candidate.get("publicPrice") or candidate.get("price") or candidate.get("sellingPrice") or ""
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
    # Provenance is optional for legacy Tawreed candidate artifacts. New
    # Excel-target candidates populate these fields so an approval can retain
    # the catalog and identity evidence that produced it.
    matching_source: str = ""
    matching_source_label: str = ""
    target_key: str = ""
    source_file: str = ""
    identity_evidence_kind: str = ""
    identity_evidence: str = ""
    compatibility_status: str = ""
    compatibility_rejection: str = ""
    # Keep the explicit Excel names as persisted aliases for older callers.
    excel_target_key: str = ""
    excel_target_source_file: str = ""
    candidate_method: str = ""
    score_margin: float = 0.0
    shared_brand_tokens: tuple[str, ...] = ()
    review_status: str = ""
    excel_target_row_key: str = ""
    excel_target_source_row: int = 0
    ranking_tier: int = 4

    def to_dict(self) -> dict[str, Any]:
        """Return dict representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewCandidateOption:
        """Create from dict representation."""
        payload = dict(data)
        # New Excel-target writers call these fields ``source_kind`` and
        # ``source_label``.  Normalize both spellings at the model boundary.
        if not payload.get("matching_source"):
            payload["matching_source"] = payload.get("source_kind", "")
        if not payload.get("matching_source_label"):
            payload["matching_source_label"] = payload.get("source_label", "")
        if not payload.get("source_file"):
            payload["source_file"] = payload.get("candidate_source_file", "")
        if not payload.get("excel_target_key"):
            payload["excel_target_key"] = payload.get("target_key", "")
        if not payload.get("excel_target_source_file"):
            payload["excel_target_source_file"] = payload.get("source_file", "")
        if not payload.get("excel_target_row_key"):
            payload["excel_target_row_key"] = payload.get("target_row_key", "")
        if not payload.get("excel_target_source_row"):
            payload["excel_target_source_row"] = payload.get("source_row_number", 0)
        if not payload.get("review_status"):
            payload["review_status"] = payload.get("compatibility_status", "")
        if "shared_brand_tokens" in payload:
            payload["shared_brand_tokens"] = _coerce_tokens(
                payload["shared_brand_tokens"]
            )
        try:
            payload["score_margin"] = float(payload.get("score_margin", 0.0) or 0.0)
        except (TypeError, ValueError):
            payload["score_margin"] = 0.0
        try:
            payload["excel_target_source_row"] = int(
                payload.get("excel_target_source_row", 0) or 0
            )
        except (TypeError, ValueError):
            payload["excel_target_source_row"] = 0
        try:
            payload["ranking_tier"] = int(payload.get("ranking_tier", 4) or 4)
        except (TypeError, ValueError):
            payload["ranking_tier"] = 4
        field_names = {field.name for field in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in payload.items() if key in field_names})

    @property
    def source_kind(self) -> str:
        """Compatibility alias used by Excel-target artifact writers."""
        return self.matching_source

    @property
    def source_label(self) -> str:
        """Compatibility alias used by Excel-target artifact writers."""
        return self.matching_source_label
def review_candidate_options(
    decision: MatchDecision, limit: int = 5
) -> list[ReviewCandidateOption]:
    """Extract top N review options from match diagnostics."""
    if not decision or not decision.diagnostics:
        return []
    selected = _selected_review_diagnostics(
        decision.diagnostics, normalize_candidate_limit(limit)
    )
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


def _coerce_tokens(value: object) -> tuple[str, ...]:
    """Normalize persisted token metadata without breaking old JSON artifacts."""
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        return ()
    return tuple(str(token).strip() for token in values if str(token).strip())
