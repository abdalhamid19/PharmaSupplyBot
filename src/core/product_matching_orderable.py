"""Orderable acceptance logic for product matching."""

from __future__ import annotations

from typing import Any

from .candidate_identity import candidate_has_store_product_id


def _orderable_acceptance(
    candidate: dict[str, Any], acceptance: tuple[bool, str, str]
) -> tuple[bool, str, str]:
    """Reject otherwise-accepted candidates that cannot be used for ordering."""
    if acceptance[0] and not candidate_has_store_product_id(candidate):
        return False, "", "Candidate missing orderable storeProductId"
    return acceptance
