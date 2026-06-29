"""CSV row building for Tawreed match logs."""

from __future__ import annotations

from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision
from ..core.utils.excel import Item
from .tawreed_match_logs_helpers import candidate_name_fields


def match_log_csv_rows(item: Item, decision: MatchDecision) -> list[dict[str, object]]:
    """Build CSV rows for all candidates considered during item matching."""
    from .tawreed_match_logs_helpers import sorted_diagnostics, MAX_DETAILED_MATCH_CANDIDATES
    rows: list[dict[str, object]] = []
    for rank, diagnostic in enumerate(
        sorted_diagnostics(decision)[:MAX_DETAILED_MATCH_CANDIDATES], start=1
    ):
        rows.append(_match_log_csv_row(item, decision, diagnostic, rank))
    return rows


def _match_log_csv_row(
    item: Item,
    decision: MatchDecision,
    diagnostic: CandidateMatchDiagnostic,
    rank: int,
) -> dict[str, object]:
    """Build one CSV row for one candidate considered during matching."""
    breakdown = diagnostic.breakdown
    row = _shared_csv_fields(item, decision, diagnostic, rank)
    row.update(_score_csv_fields(diagnostic, breakdown))
    return row


def _shared_csv_fields(
    item: Item,
    decision: MatchDecision,
    diagnostic: CandidateMatchDiagnostic,
    rank: int,
) -> dict[str, object]:
    """Return the shared CSV columns for one candidate considered during matching."""
    fields = _item_and_candidate_csv_fields(item, decision, diagnostic, rank)
    fields.update(_best_match_csv_fields(decision))
    return fields


def _item_and_candidate_csv_fields(
    item: Item,
    decision: MatchDecision,
    diagnostic: CandidateMatchDiagnostic,
    rank: int,
) -> dict[str, object]:
    """Return the item-level and candidate-level CSV columns."""
    fields = {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "final_reason": decision.final_reason,
        "candidate_rank": rank,
        "query": diagnostic.query,
        "row_index": diagnostic.row_index,
    }
    fields.update(_candidate_csv_fields(diagnostic))
    return fields


def _candidate_csv_fields(diagnostic: CandidateMatchDiagnostic) -> dict[str, object]:
    """Return the candidate-name and availability CSV columns."""
    candidate_names = candidate_name_fields(diagnostic)
    return {
        "product_name_en": candidate_names["product_name_en"],
        "product_name_ar": candidate_names["product_name_ar"],
        "available_quantity": diagnostic.candidate.get("availableQuantity"),
        "products_count": diagnostic.candidate.get("productsCount"),
        "store_product_id": diagnostic.candidate.get("storeProductId"),
    }


def _best_match_csv_fields(decision: MatchDecision) -> dict[str, object]:
    """Return the shared CSV columns derived from the final best match."""
    return {
        "best_match_query": decision.best_match.query if decision.best_match else "",
        "best_match_row_index": decision.best_match.row_index
        if decision.best_match
        else "",
        "best_match_score": decision.best_match.score if decision.best_match else "",
    }


def _score_csv_fields(
    diagnostic: CandidateMatchDiagnostic, breakdown
) -> dict[str, object]:
    """Return the score-related CSV columns for one candidate."""
    return {
        "total_score": round(diagnostic.score, 6),
        "sequence_score": round(breakdown.sequence_score, 6),
        "overlap_score": round(breakdown.overlap_score, 6),
        "numeric_overlap": round(breakdown.numeric_overlap, 6),
        "exact_bonus": round(breakdown.exact_bonus, 6),
        "availability_bonus": round(breakdown.availability_bonus, 6),
        "sort_key": str(diagnostic.sort_key),
        "accepted": diagnostic.accepted,
        "accepted_reason": diagnostic.accepted_reason,
        "rejection_reason": diagnostic.rejection_reason,
    }


__all__ = [
    "match_log_csv_rows",
    "_match_log_csv_row",
    "_shared_csv_fields",
    "_item_and_candidate_csv_fields",
    "_candidate_csv_fields",
    "_best_match_csv_fields",
    "_score_csv_fields",
]
