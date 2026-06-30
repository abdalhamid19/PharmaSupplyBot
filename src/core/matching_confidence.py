"""Calculate product matching confidence based on lexical and domain factors."""

from __future__ import annotations

import re

from ..core.drug_matching.normalization.normalizer import components_match, parse_drug
from ..core.manufacturer_identity import (
    extract_manufacturer_from_candidate,
    extract_manufacturer_from_name,
    manufacturer_conflict,
)
from ..core.matching_types import MatchDecision
from ..core.utils.excel import Item


def match_confidence(decision: MatchDecision, item: Item, query: str) -> float:
    """Compute matching confidence of the current decision for an item."""
    if not decision.best_match:
        return 0.0
    match = decision.best_match
    _ = query  # Kept for API compatibility
    req = parse_drug(item.name)
    cand_name = (
        match.data.get("productNameEn")
        or match.data.get("productNameEnFallback")
        or ""
    )
    off = parse_drug(cand_name)
    off.is_synthetic = bool(match.data.get("productNameEnSynthetic"))

    f1 = min(1.0, max(0.0, match.score / 20.0))
    f2 = 1.0 if _is_exact_brand(req, off) else 0.5
    f3 = 1.0 if _is_exact_dosage(req, off) else 0.3
    f4 = 1.0 if components_match(req, off)[0] else 0.0
    f5 = 0.8 if int(match.data.get("availableQuantity") or 0) > 0 else 0.4

    q_mfg = extract_manufacturer_from_name(item.name)
    c_mfg = extract_manufacturer_from_candidate(
        cand_name,
        match.data.get("companyName"),
        match.data.get("supplierName"),
    )
    f6 = 0.0 if manufacturer_conflict(q_mfg, c_mfg) else 1.0

    weights = [0.25, 0.22, 0.22, 0.13, 0.05, 0.13]
    factors = [f1, f2, f3, f4, f5, f6]
    return sum(f * w for f, w in zip(factors, weights))


def _is_brand_clean(brand: str) -> str:
    """Return a alphanumeric uppercase cleaned brand name."""
    return re.sub(r"[^A-Z0-9]", "", brand.strip().upper())


def _is_exact_brand(req, off) -> bool:
    """Return whether the requested and offered brands are an exact match."""
    r_brand = _is_brand_clean(req.brand)
    o_brand = _is_brand_clean(off.brand)
    return r_brand == o_brand and bool(r_brand)


def _is_exact_dosage(req, off) -> bool:
    """Return whether the requested and offered dosages match exactly."""
    return req.dosage_nums == off.dosage_nums and req.dosage_units == off.dosage_units
