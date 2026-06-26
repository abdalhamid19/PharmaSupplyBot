"""Candidate conversion helpers for live-order AI matching."""

from __future__ import annotations

from typing import Any

from .candidate_identity import candidate_store_product_id
from .matching_models import MatchDecision, SearchMatch


def candidate_name(candidate: dict[str, Any]) -> str:
    """Return the English display name used in AI prompts."""
    return str(
        candidate.get("productNameEn")
        or candidate.get("productNameEnFallback")
        or candidate.get("productName")
        or ""
    )


def candidate_ar(candidate: dict[str, Any]) -> str:
    """Return the Arabic display name used in AI prompts."""
    return str(candidate.get("productName") or "")


def candidate_price(candidate: dict[str, Any]) -> object:
    """Return candidate price when Tawreed exposes one."""
    return (
        candidate.get("retailPrice") or candidate.get("publicPrice") or
        candidate.get("price") or candidate.get("sellingPrice")
    )


def ai_candidates(decision: MatchDecision) -> list[tuple[dict, float, int]]:
    """Return verifier-compatible candidates from match diagnostics."""
    return [
        (record_from_diagnostic(diag), float(diag.score), diag.row_index)
        for diag in decision.diagnostics[:8]
    ]


def record_from_diagnostic(diag) -> dict[str, Any]:
    """Return one AI-search record from a Tawreed diagnostic."""
    candidate = diag.candidate
    return {
        "product_name_en": candidate_name(candidate),
        "product_name_ar": candidate_ar(candidate),
        "store_product_id": candidate_store_product_id(candidate),
        "price": candidate_price(candidate),
        "_raw": candidate,
        "_query": diag.query,
        "_row_index": diag.row_index,
    }


def match_from_record(record: dict[str, Any], score: float) -> SearchMatch:
    """Return a SearchMatch from an AI-selected record."""
    data = dict(record.get("_raw") or {})
    if not data:
        data = {
            "productNameEn": record.get("product_name_en", ""),
            "productName": record.get("product_name_ar", ""),
            "storeProductId": record.get("store_product_id", ""),
            "price": record.get("price", ""),
        }
    if not candidate_store_product_id(data) and record.get("store_product_id"):
        data["storeProductId"] = record.get("store_product_id")
    return SearchMatch(
        query=str(record.get("_query", "")),
        row_index=int(record.get("_row_index", 0) or 0),
        score=float(score or 0.0),
        data=data,
    )
