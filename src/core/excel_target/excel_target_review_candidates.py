"""Manual-review candidates derived exclusively from an Excel target catalog.

The normal Tawreed review candidate model is built from search diagnostics. An
Excel target has no search response, so review candidates must be derived from
the :class:`TargetProduct` rows that were actually loaded from the target
workbook.  This module keeps that conversion in the Excel-target boundary and
attaches the identity/variant evidence that a reviewer needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.core.matching_types import CandidateMatchDiagnostic
from src.core.utils.excel import Item

from .excel_target_identity import IdentifiedTarget, IdentityEvidence
from .excel_target_loader import TargetProduct
from .product_attributes import CompatibilityResult, validate_product_compatibility


@dataclass(frozen=True)
class ExcelTargetReviewCandidate:
    """One target-catalog row that can be shown to a human reviewer.

    ``product`` is always a row from the loaded Excel target catalog.  In
    particular, this object never carries a Tawreed price, availability, or
    product identifier.  ``compatibility`` is evaluated against the requested
    item even when the candidate is rejected, so a manual reviewer can see why
    it was not safe for automatic matching.
    """

    target_key: str
    product: TargetProduct
    score: float
    compatibility: CompatibilityResult
    identity_evidence: IdentityEvidence | None = None
    rejection_reason: str = ""

    @property
    def source_kind(self) -> str:
        """Return the stable source kind used by run artifacts."""
        return "excel-target"

    @property
    def source_label(self) -> str:
        """Return a target/file label suitable for persisted review data."""
        return (
            f"{self.target_key}@{self.product.source_file}"
            if self.product.source_file
            else self.target_key
        )

    @property
    def identity_evidence_kind(self) -> str:
        return self.identity_evidence.kind if self.identity_evidence else ""

    @property
    def identity_evidence_detail(self) -> str:
        return self.identity_evidence.detail if self.identity_evidence else ""

    @property
    def compatibility_status(self) -> str:
        return "compatible" if self.compatibility.accepted else "rejected"

    @property
    def compatibility_rejection(self) -> str:
        return self.compatibility.rejection_reason

    def to_review_candidate_dict(self) -> dict[str, object]:
        """Return the generic review-option shape without importing UI code.

        The manual-review persistence layer can construct its own typed option
        from this dict.  Keeping this adapter dependency-free prevents the
        Excel matcher from importing the UI/store implementation.
        """
        candidate = self.product.to_candidate_dict()
        product_id = str(candidate.get("storeProductId") or self.product.code)
        name_en = self.product.trusted_name_en
        reason = self.rejection_reason or self.compatibility_rejection
        return {
            "store_product_id": product_id,
            "name_en": name_en,
            "name_ar": self.product.name_ar,
            "supplier": f"excel-target:{self.source_label}",
            "available_quantity": 1,
            "price": float(self.product.price or 0.0),
            "score": float(self.score),
            "rejection_reason": reason,
            "orderable": bool(product_id),
            "matching_source": self.source_kind,
            "matching_source_label": self.source_label,
            "target_key": self.target_key,
            "source_file": self.product.source_file,
            "identity_evidence_kind": self.identity_evidence_kind,
            "identity_evidence": self.identity_evidence_detail,
            "compatibility_status": self.compatibility_status,
            "compatibility_rejection": self.compatibility_rejection,
            "excel_target_key": self.target_key,
            "excel_target_source_file": self.product.source_file,
        }


def build_review_candidates(
    item: Item,
    target_key: str,
    catalog: Sequence[TargetProduct],
    *,
    identified: Iterable[IdentifiedTarget] = (),
    diagnostics: Iterable[CandidateMatchDiagnostic] = (),
    limit: int | None = None,
) -> tuple[ExcelTargetReviewCandidate, ...]:
    """Build review candidates from target rows and matching evidence.

    ``identified`` is the preferred source for Arabic rows and includes the
    exact identity evidence used by the matcher.  ``diagnostics`` supplements
    it for genuine English target rows.  Diagnostics are accepted only when
    their ``storeProductId`` resolves back to a loaded ``TargetProduct``; this
    is the guard that prevents a Tawreed diagnostic from leaking into a
    Baraka review list.
    """
    by_id = _catalog_by_id(catalog)
    candidates: dict[str, ExcelTargetReviewCandidate] = {}

    for identified_target in identified:
        product = identified_target.product
        key = _product_key(product)
        if key not in by_id:
            continue
        compatibility = validate_product_compatibility(item.name, product.name_ar)
        candidate = ExcelTargetReviewCandidate(
            target_key=target_key,
            product=product,
            score=float(identified_target.evidence.confidence) * 20.0,
            compatibility=compatibility,
            identity_evidence=identified_target.evidence,
            rejection_reason=compatibility.rejection_reason,
        )
        _keep_best(candidates, key, candidate)

    for diagnostic in diagnostics:
        raw = diagnostic.candidate
        product = by_id.get(str(raw.get("storeProductId") or ""))
        if product is None:
            continue
        compatibility = validate_product_compatibility(item.name, product.name_ar)
        evidence = IdentityEvidence(
            "native_english",
            product.trusted_name_en,
            "native English supplier name",
            1.0,
        ) if product.trusted_name_en else None
        rejection = (
            compatibility.rejection_reason
            or str(getattr(diagnostic, "rejection_reason", "") or "")
        )
        candidate = ExcelTargetReviewCandidate(
            target_key=target_key,
            product=product,
            score=float(getattr(diagnostic, "score", 0.0) or 0.0),
            compatibility=compatibility,
            identity_evidence=evidence,
            rejection_reason=rejection,
        )
        _keep_best(candidates, _product_key(product), candidate)

    ordered = sorted(
        candidates.values(),
        key=lambda candidate: (
            candidate.score,
            candidate.identity_evidence.confidence
            if candidate.identity_evidence
            else 0.0,
            candidate.product.code,
            candidate.product.name,
        ),
        reverse=True,
    )
    if limit is not None:
        ordered = ordered[: max(0, int(limit))]
    return tuple(ordered)


def _catalog_by_id(catalog: Sequence[TargetProduct]) -> dict[str, TargetProduct]:
    return {_product_key(product): product for product in catalog}


def _product_key(product: TargetProduct) -> str:
    candidate = product.to_candidate_dict()
    return str(candidate.get("storeProductId") or product.code or product.name)


def _keep_best(
    candidates: dict[str, ExcelTargetReviewCandidate],
    key: str,
    candidate: ExcelTargetReviewCandidate,
) -> None:
    existing = candidates.get(key)
    if existing is None or candidate.score > existing.score:
        candidates[key] = candidate


__all__ = [
    "ExcelTargetReviewCandidate",
    "build_review_candidates",
]
