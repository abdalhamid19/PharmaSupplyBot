"""Extract and compare manufacturer identity from explicit product fields.

Design contract: manufacturers are **recognised, never guessed**.

The previous implementation treated "the last non-generic token of a product
name" as the manufacturer. Measured against 1232 distinct item names in the
live manual-review store, that heuristic claimed a manufacturer for 99.8% of
names and invented one for 99.0% (dosage words like EXTRA, packaging units
like SACHETS, active ingredients like ACYCLOVIR, brands like PANADOL). Those
phantom manufacturers collided with real `companyName` values and blocked
legitimate matches from being saved.

Now:
  * item/query side  -> recognise curated KNOWN_MANUFACTURERS tokens only
  * candidate side   -> use explicit companyName / supplierName only
  * unknown on either side -> no manufacturer, hence no conflict
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.core.drug_matching.normalization.normalizer_manufacturer_extraction import (
    KNOWN_MANUFACTURERS,
)
from src.core.matching.product_matching_helpers import normalize_text


__all__ = [
    "extract_manufacturer_from_name",
    "extract_manufacturer_from_candidate",
    "manufacturer_conflict",
    "KNOWN_MANUFACTURERS",
]

_PARENTHESISED_TOKEN_RE = re.compile(r"\(([^)]*)\)")


def extract_manufacturer_from_name(name: str) -> str | None:
    """Return a curated manufacturer named inside the text, else None.

    Only tokens present in KNOWN_MANUFACTURERS are returned, so product
    words, dosage descriptors, and packaging units are never mistaken for
    companies. Parenthesised manufacturers win because they are the most
    explicit form; otherwise the last recognised token wins (manufacturers
    are conventionally written at the end of Egyptian pharmacy item names).
    """
    if not name:
        return None

    parenthesised = _parenthesised_manufacturer(name)
    if parenthesised:
        return parenthesised

    recognised = [
        token for token in normalize_text(name).split()
        if token in KNOWN_MANUFACTURERS
    ]
    return recognised[-1] if recognised else None


def _parenthesised_manufacturer(name: str) -> str | None:
    """Return a curated manufacturer written in parentheses, e.g. "(ORCHIDIA)"."""
    for group in _PARENTHESISED_TOKEN_RE.findall(name):
        for token in normalize_text(group).split():
            if token in KNOWN_MANUFACTURERS:
                return token
    return None


def extract_manufacturer_from_candidate(
    candidate_name: str,
    company_name: str | None = None,
    supplier_name: str | None = None,
) -> str | None:
    """Return the candidate's manufacturer from explicit API fields only.

    `candidate_name` is accepted for call-site compatibility but deliberately
    unused: guessing a company from a product name is what produced phantom
    conflicts. When Tawreed sends no company or supplier, the answer is None.
    """
    del candidate_name  # explicit fields only; never guess from the name
    return _first_token(company_name) or _first_token(supplier_name)


def _first_token(value: str | None) -> str | None:
    """Return the leading normalized token of an explicit company field."""
    if not value:
        return None
    tokens = normalize_text(value).split()
    return tokens[0] if tokens else None


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
