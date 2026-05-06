"""Candidate field helpers for match-only summary artifacts."""

from __future__ import annotations

import json
from typing import Any

from ..core.matching_models import CandidateMatchDiagnostic, MatchDecision
from .tawreed_match_only_constants import MATCH_ONLY_API_KEYS


def candidate_summary_fields(
    decision: MatchDecision | None,
    diagnostic: CandidateMatchDiagnostic,
    rank: int,
) -> dict[str, object]:
    """Return candidate identity, scoring, and API fields for a summary row."""
    fields = _candidate_identity_fields(decision, diagnostic, rank)
    fields.update(_score_fields(diagnostic))
    fields.update(_api_fields(diagnostic.candidate))
    return fields


def sorted_diagnostics(
    decision: MatchDecision | None,
) -> list[CandidateMatchDiagnostic]:
    """Return candidate diagnostics sorted from best to worst."""
    if not decision:
        return []
    return sorted(
        decision.diagnostics, key=lambda current: current.sort_key, reverse=True
    )


def best_match_attr(decision: MatchDecision | None, name: str) -> object:
    """Return an attribute from the best match when one exists."""
    if not decision or not decision.best_match:
        return ""
    return getattr(decision.best_match, name)


def _candidate_identity_fields(decision, diagnostic, rank: int) -> dict[str, object]:
    """Return candidate identity fields not directly copied from the API payload."""
    return {
        "candidate_rank": rank,
        "candidate_source": _candidate_source(diagnostic.candidate),
        "is_best_match": _is_best_match(decision, diagnostic),
        "query": diagnostic.query,
        "row_index": diagnostic.row_index,
    }


def _score_fields(diagnostic: CandidateMatchDiagnostic) -> dict[str, object]:
    """Return matching-score fields for one candidate."""
    b = diagnostic.breakdown
    return {
        "total_score": round(diagnostic.score, 6),
        "sequence_score": round(b.sequence_score, 6),
        "overlap_score": round(b.overlap_score, 6),
        "numeric_overlap": round(b.numeric_overlap, 6),
        "exact_bonus": round(b.exact_bonus, 6),
        "availability_bonus": round(b.availability_bonus, 6),
        "critical_penalty": round(b.critical_penalty, 6),
        "extra_token_penalty": round(b.extra_token_penalty, 6),
        "semantic_penalty": round(b.semantic_penalty, 6),
        "sort_key": str(diagnostic.sort_key),
        "accepted": diagnostic.accepted,
        "accepted_reason": diagnostic.accepted_reason,
        "rejection_reason": diagnostic.rejection_reason,
    }


def _api_fields(candidate: dict[str, Any]) -> dict[str, object]:
    """Return useful Tawreed API fields plus a compact raw payload snapshot."""
    row = {f"api_{key}": candidate.get(key, "") for key in MATCH_ONLY_API_KEYS}
    row["api_raw_candidate_json"] = json.dumps(
        candidate, ensure_ascii=False, sort_keys=True, default=str
    )
    return row


def _is_best_match(decision, diagnostic: CandidateMatchDiagnostic) -> bool:
    """Return whether a diagnostic corresponds to the final best match."""
    best = decision.best_match if decision else None
    return bool(
        best
        and best.query == diagnostic.query
        and best.row_index == diagnostic.row_index
    )


def _candidate_source(candidate: dict[str, Any]) -> str:
    """Return whether a candidate came from Tawreed API or the DOM fallback."""
    store_product_id = str(candidate.get("storeProductId") or "")
    if store_product_id.startswith("dom-row-") or candidate.get(
        "productNameEnSynthetic"
    ):
        return "dom_fallback"
    return "site_api"
