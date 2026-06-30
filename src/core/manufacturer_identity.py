"""Extract and compare manufacturer identity from product names."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from src.core.product_matching_helpers import (
    _GENERIC_IDENTITY_TOKENS,
    normalize_text,
)


__all__ = [
    "extract_manufacturer_from_name",
    "extract_manufacturer_from_candidate",
    "manufacturer_conflict",
]


def extract_manufacturer_from_name(name: str) -> str | None:
    """Extract last non-numeric, non-generic token from product name."""
    if not name:
        return None
    tokens = normalize_text(name).split()
    for token in reversed(tokens):
        if token.isdigit():
            continue
        if token in _GENERIC_IDENTITY_TOKENS:
            continue
        return token
    return None


def extract_manufacturer_from_candidate(
    candidate_name: str,
    company_name: str | None = None,
    supplier_name: str | None = None,
) -> str | None:
    """Extract manufacturer from candidate, preferring explicit fields."""
    if company_name:
        normalized = normalize_text(company_name)
        tokens = normalized.split()
        return tokens[0] if tokens else None
    if supplier_name:
        normalized = normalize_text(supplier_name)
        tokens = normalized.split()
        return tokens[0] if tokens else None
    return extract_manufacturer_from_name(candidate_name)


def manufacturer_conflict(
    query_company: str | None,
    candidate_company: str | None,
    threshold: float = 0.85,
) -> bool:
    """Check if two manufacturer names conflict (different companies)."""
    if not query_company or not candidate_company:
        return False
    q_norm = normalize_text(query_company)
    c_norm = normalize_text(candidate_company)
    if q_norm == c_norm:
        return False
    ratio = SequenceMatcher(None, q_norm, c_norm).ratio()
    return ratio < threshold
