"""Match-only summary artifacts for Tawreed - unified module."""

from __future__ import annotations

import json
from typing import Any

from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision
from ..core.utils.excel import Item
from .tawreed_artifacts import append_csv_artifact
from .tawreed_match_logs import OrderResultSummary
from .tawreed_timing import timing_summary_fields

MATCH_ONLY_SUMMARY_LABEL = "match_only_summary"
MATCH_ONLY_API_KEYS = (
    "productId",
    "storeProductId",
    "productNameEn",
    "productName",
    "productNameEnFallback",
    "productNameEnSynthetic",
    "availableQuantity",
    "productsCount",
    "storeName",
    "supplierName",
    "companyName",
    "discountPercent",
    "retailPrice",
    "salePrice",
    "currency",
    "priority",
    "stockLevel",
    "minOrderDiff",
    "imageContentId",
)


# ============================================================================
# Constants
# ============================================================================


# ============================================================================
# Candidate field helpers (from tawreed_match_only_fields.py)
# ============================================================================

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


# ============================================================================
# Row builders (from tawreed_match_only_rows.py)
# ============================================================================

def match_only_summary_rows(
    item: Item, summary: OrderResultSummary, decision: MatchDecision | None
) -> list[dict[str, object]]:
    """Build one summary row per candidate considered during match-only mode."""
    diagnostics = sorted_diagnostics(decision)
    if not diagnostics:
        return [_base_row(item, summary, decision)]
    return [
        _candidate_row(item, summary, decision, diagnostic, rank)
        for rank, diagnostic in enumerate(diagnostics, start=1)
    ]


def _candidate_row(item, summary, decision, diagnostic, rank) -> dict[str, object]:
    """Return a candidate-level match-only summary row."""
    row = _base_row(item, summary, decision)
    row.update(candidate_summary_fields(decision, diagnostic, rank))
    return row


def _base_row(
    item: Item, summary: OrderResultSummary, decision: MatchDecision | None
) -> dict[str, object]:
    """Return item-level match-only fields shared by every row."""
    return {
        "item_code": item.code, "item_name": item.name, "item_qty": item.qty,
        "status": summary.status, "reason": summary.reason,
        "final_reason": decision.final_reason if decision else "",
        "best_match_query": best_match_attr(decision, "query"),
        "best_match_row_index": best_match_attr(decision, "row_index"),
        "best_match_score": best_match_attr(decision, "score"),
        "matched_query": summary.matched_query,
        "searched_queries_count": summary.searched_queries_count,
        "searched_queries": summary.searched_queries,
        "elapsed_seconds": round(summary.elapsed_seconds, 3),
        "match_elapsed_seconds": round(summary.match_elapsed_seconds, 3),
        **timing_summary_fields(summary.timing_seconds),
    }


# ============================================================================
# CSV summary writer (from tawreed_match_only_summary.py)
# ============================================================================

def append_match_only_summary(
    profile_key: str,
    item: Item,
    summary: OrderResultSummary,
    decision: MatchDecision | None,
    label_suffix: str | None = None,
) -> None:
    """Append match-only summary rows without touching order-result summaries."""
    rows = match_only_summary_rows(item, summary, decision)
    append_csv_artifact(
        profile_key, MATCH_ONLY_SUMMARY_LABEL, rows, label_suffix=label_suffix
    )


__all__ = [
    "MATCH_ONLY_SUMMARY_LABEL",
    "MATCH_ONLY_API_KEYS",
    "candidate_summary_fields",
    "sorted_diagnostics",
    "best_match_attr",
    "match_only_summary_rows",
    "append_match_only_summary",
]
