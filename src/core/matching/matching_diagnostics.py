"""Helpers for selecting safe diagnostic candidates for user-facing output."""

from __future__ import annotations

from collections.abc import Iterable

from ..matching_types import CandidateMatchDiagnostic
from .candidate_identity import candidate_has_store_product_id
from .product_matching_acceptance import identity_conflict_rejection_reason


def is_recognized_unorderable_diagnostic(
    diagnostic: CandidateMatchDiagnostic,
) -> bool:
    """Return whether a diagnostic identifies a product that cannot be ordered.

    A missing ``storeProductId`` is an availability/orderability problem only
    when the candidate is otherwise identity-compatible. Hard identity
    conflicts, such as MILGA versus MAN, must never be surfaced as the
    requested product's recognized out-of-stock name.
    """
    candidate = diagnostic.candidate or {}
    if candidate_has_store_product_id(candidate):
        return False
    if identity_conflict_rejection_reason(diagnostic.query, candidate):
        return False
    return _has_recognized_unorderable_rejection(diagnostic)


def _has_recognized_unorderable_rejection(
    diagnostic: CandidateMatchDiagnostic,
) -> bool:
    """Classify soft acceptance failures as recognized but unavailable."""
    reason = str(diagnostic.rejection_reason or "").casefold()
    if "candidate missing orderable storeproductid" in reason:
        return True

    hard_rejections = (
        "component mismatch",
        "identity token",
        "different_brand",
        "semantic token",
    )
    if any(text in reason for text in hard_rejections):
        return False

    score = float(diagnostic.score or 0.0)
    if "unrequested numeric" in reason and score >= 9.0:
        return True
    return score >= 12.0


def best_recognized_unorderable_diagnostic(
    diagnostics: Iterable[CandidateMatchDiagnostic] | None,
) -> CandidateMatchDiagnostic | None:
    """Return the strongest identity-compatible candidate without an orderable ID."""
    eligible = [
        diagnostic
        for diagnostic in diagnostics or ()
        if is_recognized_unorderable_diagnostic(diagnostic)
    ]
    return max(eligible, key=lambda diagnostic: diagnostic.sort_key, default=None)


__all__ = [
    "best_recognized_unorderable_diagnostic",
    "is_recognized_unorderable_diagnostic",
]
