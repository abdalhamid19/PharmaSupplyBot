"""Manual-review candidates derived exclusively from an Excel target catalog.

The normal Tawreed review candidate model is built from search diagnostics. An
Excel target has no search response, so review candidates must be derived from
the :class:`TargetProduct` rows that were actually loaded from the target
workbook.  This module keeps that conversion in the Excel-target boundary and
attaches the identity/variant evidence that a reviewer needs.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from src.core.matching_types import CandidateMatchDiagnostic
from src.core.utils.excel import Item

from .excel_target_identity import IdentifiedTarget, IdentityEvidence
from .excel_target_loader import TargetProduct
from .product_attributes import CompatibilityResult, validate_product_compatibility
from .excel_target_review_discovery import ReviewDiscoveryHit


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
    candidate_method: str = ""
    score_margin: float = 0.0
    shared_brand_tokens: tuple[str, ...] = ()
    review_status_hint: str = ""

    def __post_init__(self) -> None:
        """Give every candidate an explicit review state for artifact consumers."""
        if not self.candidate_method:
            object.__setattr__(
                self,
                "candidate_method",
                _candidate_method(self.identity_evidence_kind),
            )
        if not self.shared_brand_tokens:
            object.__setattr__(
                self,
                "shared_brand_tokens",
                _shared_brand_tokens(
                    self.identity_evidence.canonical_brand
                    if self.identity_evidence
                    else "",
                    self.product.trusted_name_en or self.product.name_ar,
                ),
            )

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

    @property
    def review_status(self) -> str:
        """Return a human-review state without treating it as auto-match evidence."""
        if self.review_status_hint:
            return self.review_status_hint
        if self.compatibility.accepted:
            return "compatible"
        reason = self.compatibility.rejection_reason.casefold()
        if not reason or "not proven" in reason or "unknown" in reason:
            return "variant_unproven"
        return "variant_conflict"

    @property
    def ranking_tier(self) -> int:
        """Return the review-only priority tier for deterministic ordering."""
        kind = self.identity_evidence_kind or self.candidate_method
        if kind in {
            "native_english",
            "safe_alias",
            "tawreed_catalog",
            "dictionary",
            "cached_translation",
            "tawreed_dictionary",
            "egyptian_dictionary",
        }:
            return 0 if self.compatibility.accepted else 1
        if kind == "review_identity":
            return 2
        if kind == "review_identity_prefix":
            return 3
        if kind in {
            "review_fuzzy",
            "english_fuzzy",
            "arabic_fuzzy",
            "cross_language_alias",
            "cohere_translation",
            "cached_cohere",
        }:
            return 4
        return 4

    @property
    def excel_target_row_key(self) -> str:
        return excel_target_row_key(self.target_key, self.product)

    @property
    def excel_target_source_row(self) -> int:
        return int(self.product.source_row_number or 0)

    def to_review_candidate_dict(self) -> dict[str, object]:
        """Return the generic review-option shape without importing UI code.

        The manual-review persistence layer can construct its own typed option
        from this dict.  Keeping this adapter dependency-free prevents the
        Excel matcher from importing the UI/store implementation.
        """
        product_id = self.product.store_product_id
        name_en = self.product.trusted_name_en
        reason = self.rejection_reason or self.compatibility_rejection
        return {
            "store_product_id": product_id,
            "name_en": name_en,
            "name_ar": self.product.name_ar,
            "supplier": f"excel-target:{self.source_label}",
            "available_quantity": 1,
            # Preserve an unknown catalog price as ``None``.  A blank Excel
            # cell must not become a synthetic zero-price offer in review
            # artifacts or subsequent persistence.
            "price": (
                float(self.product.price)
                if self.product.price is not None
                else None
            ),
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
            "review_status": self.review_status,
            "ranking_tier": self.ranking_tier,
            "candidate_method": self.candidate_method,
            "score_margin": float(self.score_margin),
            "shared_brand_tokens": self.shared_brand_tokens,
            "excel_target_key": self.target_key,
            "excel_target_source_file": self.product.source_file,
            "excel_target_row_key": self.excel_target_row_key,
            "excel_target_source_row": self.excel_target_source_row,
        }


def build_review_candidates(
    item: Item,
    target_key: str,
    catalog: Sequence[TargetProduct],
    *,
    identified: Iterable[IdentifiedTarget] = (),
    diagnostics: Iterable[CandidateMatchDiagnostic] = (),
    discovery_hits: Iterable[ReviewDiscoveryHit] = (),
    limit: int | None = None,
    catalog_by_id: Mapping[str, TargetProduct | tuple[TargetProduct, ...]] | None = None,
) -> tuple[ExcelTargetReviewCandidate, ...]:
    """Build review candidates from target rows and matching evidence.

    ``identified`` is the preferred source for Arabic rows and includes the
    exact identity evidence used by the matcher.  ``diagnostics`` supplements
    it for genuine English target rows.  Diagnostics are accepted only when
    their ``storeProductId`` resolves back to a loaded ``TargetProduct``; this
    is the guard that prevents a Tawreed diagnostic from leaking into a
    Baraka review list.
    """
    by_id = catalog_by_id if catalog_by_id is not None else _catalog_by_id(catalog)
    catalog_row_keys = {_product_key(target_key, product) for product in catalog}
    candidates: dict[str, ExcelTargetReviewCandidate] = {}

    for hit in discovery_hits:
        product = hit.product
        key = _product_key(target_key, product)
        if key not in catalog_row_keys:
            continue
        compatibility = validate_product_compatibility(item.name, product.name_ar)
        candidate = ExcelTargetReviewCandidate(
            target_key=target_key,
            product=product,
            score=float(hit.score),
            score_margin=float(hit.score_margin),
            compatibility=compatibility,
            identity_evidence=IdentityEvidence(
                "review_fuzzy",
                hit.strategy,
                f"{hit.strategy} review candidate ({hit.score:.1f}, margin {hit.score_margin:.1f})",
                max(0.0, min(1.0, hit.score / 100.0)),
            ),
            rejection_reason=compatibility.rejection_reason,
            candidate_method=hit.strategy,
            shared_brand_tokens=hit.shared_brand_tokens,
            review_status_hint=hit.review_status,
        )
        _keep_best(candidates, key, candidate)

    for identified_target in identified:
        product = identified_target.product
        key = _product_key(target_key, product)
        if key not in catalog_row_keys:
            continue
        compatibility = validate_product_compatibility(item.name, product.name_ar)
        candidate = ExcelTargetReviewCandidate(
            target_key=target_key,
            product=product,
            score=float(identified_target.evidence.confidence) * 20.0,
            compatibility=compatibility,
            identity_evidence=identified_target.evidence,
            rejection_reason=compatibility.rejection_reason,
            candidate_method=_candidate_method(identified_target.evidence.kind),
        )
        _keep_best(candidates, key, candidate)

    for diagnostic in diagnostics:
        raw = diagnostic.candidate
        products = _products_for_id(by_id, str(raw.get("storeProductId") or ""))
        if not products:
            continue
        for product in products:
            compatibility = validate_product_compatibility(item.name, product.name_ar)
            evidence = IdentityEvidence(
                "review_fuzzy",
                product.trusted_name_en,
                "English fuzzy target-row candidate",
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
                candidate_method="english_fuzzy",
            )
            _keep_best(candidates, _product_key(target_key, product), candidate)

    ordered = sorted(candidates.values(), key=_candidate_order_key)
    if limit is not None:
        ordered = ordered[: max(0, int(limit))]
    return tuple(ordered)


def _catalog_by_id(
    catalog: Sequence[TargetProduct],
) -> dict[str, tuple[TargetProduct, ...]]:
    grouped: dict[str, list[TargetProduct]] = {}
    for product in catalog:
        grouped.setdefault(str(product.store_product_id), []).append(product)
    return {key: tuple(value) for key, value in grouped.items()}


def _products_for_id(
    catalog_by_id: Mapping[str, TargetProduct | tuple[TargetProduct, ...]],
    product_id: str,
) -> tuple[TargetProduct, ...]:
    value = catalog_by_id.get(product_id)
    if value is None:
        return ()
    if isinstance(value, TargetProduct):
        return (value,)
    return tuple(value)


def _product_key(target_key: str, product: TargetProduct) -> str:
    return excel_target_row_key(target_key, product)


def _keep_best(
    candidates: dict[str, ExcelTargetReviewCandidate],
    key: str,
    candidate: ExcelTargetReviewCandidate,
) -> None:
    existing = candidates.get(key)
    if existing is None or _candidate_order_key(candidate) < _candidate_order_key(existing):
        candidates[key] = candidate


def _candidate_order_key(
    candidate: ExcelTargetReviewCandidate,
) -> tuple[int, int, float, float, str]:
    """Rank compatible review rows before incompatible evidence."""
    compatibility_rank = _compatibility_rank(candidate)
    return (
        compatibility_rank,
        candidate.ranking_tier,
        -float(candidate.score),
        -float(candidate.score_margin),
        candidate.excel_target_row_key,
    )


def _compatibility_rank(candidate: ExcelTargetReviewCandidate) -> int:
    """Return a deterministic rank for explicit attribute compatibility."""
    if candidate.compatibility.accepted:
        return 0
    if candidate.review_status == "variant_unproven":
        return 1
    return 2


__all__ = [
    "ExcelTargetReviewCandidate",
    "build_review_candidates",
    "excel_target_row_key",
]


_WHITESPACE_RE = re.compile(r"\s+")
_BRAND_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+/-]*")
_NON_BRAND_TOKENS = {
    "AMP",
    "AMPOULE",
    "CAP",
    "CAPS",
    "CAPSULE",
    "CAPSULES",
    "CREAM",
    "FILM",
    "GEL",
    "INJ",
    "INJECTION",
    "ML",
    "MG",
    "SYP",
    "SYRUP",
    "TAB",
    "TABS",
    "TABLET",
    "TABLETS",
}


def _normalize_row_component(value: object, *, path: bool = False) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    if path:
        text = text.replace("\\", "/")
    return _WHITESPACE_RE.sub(" ", text)


def excel_target_row_key(target_key: str, product: TargetProduct) -> str:
    """Return the deterministic identity of one target workbook row.

    The product code alone is intentionally insufficient: a workbook may
    contain duplicate codes for different strengths, forms, or pack sizes.
    """
    material = "|".join(
        (
            _normalize_row_component(target_key),
            _normalize_row_component(product.source_file, path=True),
            str(int(product.source_row_number or 0)),
            _normalize_row_component(product.store_product_id),
            _normalize_row_component(product.name),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _candidate_method(identity_kind: str) -> str:
    return {
        "review_fuzzy": "english_fuzzy",
        "safe_alias": "safe_alias",
        "cohere_translation": "cached_cohere",
        "cached_translation": "cached_translation",
        "tawreed_catalog": "tawreed_dictionary",
        "dictionary": "egyptian_dictionary",
        "native_english": "native_english",
        "review_identity": "review_identity",
        "review_identity_prefix": "review_identity_prefix",
    }.get(identity_kind, identity_kind or "")


def _shared_brand_tokens(left: str, right: str) -> tuple[str, ...]:
    left_tokens = {
        token.upper()
        for token in _BRAND_TOKEN_RE.findall(left or "")
        if token.upper() not in _NON_BRAND_TOKENS
    }
    right_tokens = {
        token.upper()
        for token in _BRAND_TOKEN_RE.findall(right or "")
        if token.upper() not in _NON_BRAND_TOKENS
    }
    return tuple(sorted(left_tokens & right_tokens))
