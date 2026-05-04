"""Diagnostic log builders for Tawreed product matching."""

from __future__ import annotations

from dataclasses import dataclass

from ..excel import Item
from ..core.matching_models import CandidateMatchDiagnostic, MatchDecision
from .tawreed_artifacts import (
    append_csv_artifact,
    append_xlsx_artifact,
    append_text_artifact,
    write_text_artifact,
)


@dataclass(frozen=True)
class OrderItemSummary:
    """One compact execution summary row for an item processed during ordering."""

    status: str
    reason: str
    ordered_total_qty: int = 0
    matched_product_name: str = ""
    matched_query: str = ""
    selected_discount_percent: str = ""
    selected_store_name: str = ""
    searched_queries_count: int = 0
    searched_queries: str = ""
    elapsed_seconds: float = 0.0
    match_elapsed_seconds: float = 0.0


def write_match_log(bot, item: Item, decision: MatchDecision) -> None:
    """Write detailed TXT and CSV matching diagnostics for one item."""
    if not should_write_detailed_match_log(decision):
        return
    log_content = match_log_content(item, decision)
    log_label = f"match_log_{safe_item_label(item)}"
    write_text_artifact(bot.profile_key, log_label, log_content)
    append_text_artifact(
        bot.profile_key,
        "match_log_all",
        match_log_section_separator(item) + log_content,
    )
    append_csv_artifact(bot.profile_key, "match_log_all", match_log_csv_rows(item, decision))


def should_write_detailed_match_log(decision: MatchDecision) -> bool:
    """Return whether one decision needs full diagnostic logging for later review."""
    if not decision.best_match:
        return True
    best_diagnostic = _best_match_diagnostic(decision)
    if best_diagnostic is None:
        return True
    if not best_diagnostic.accepted:
        return True
    if best_diagnostic.accepted_reason != "high_token_overlap":
        return True
    if best_diagnostic.breakdown.overlap_score < 1.0:
        return True
    if best_diagnostic.breakdown.numeric_overlap not in (0.0, 1.0):
        return True
    return False


def append_order_result_summary(
    profile_key: str,
    item: Item,
    summary: OrderItemSummary,
) -> None:
    """Append one compact order-result summary row to the table artifacts."""
    row = {
        "item_code": item.code,
        "item_name": item.name,
        "item_qty": item.qty,
        "ordered_total_qty": summary.ordered_total_qty,
        "status": summary.status,
        "reason": summary.reason,
        "matched_product_name": summary.matched_product_name,
        "matched_query": summary.matched_query,
        "selected_discount_percent": summary.selected_discount_percent,
        "selected_store_name": summary.selected_store_name,
        "searched_queries_count": summary.searched_queries_count,
        "searched_queries": summary.searched_queries,
        "elapsed_seconds": round(summary.elapsed_seconds, 3),
        "match_elapsed_seconds": round(summary.match_elapsed_seconds, 3),
    }
    append_csv_artifact(profile_key, "order_result_summary", [row])
    append_xlsx_artifact(profile_key, "order_result_summary", [row])


def match_log_content(item: Item, decision: MatchDecision) -> str:
    """Build the detailed product-matching log content for one item."""
    lines = _match_log_header_lines(item, decision)
    for candidate_index, diagnostic in enumerate(_sorted_diagnostics(decision), start=1):
        lines.extend(candidate_log_lines(candidate_index, diagnostic))
    return "\n".join(lines) + "\n"


def _best_match_diagnostic(decision: MatchDecision) -> CandidateMatchDiagnostic | None:
    """Return the diagnostic that corresponds to the accepted best match."""
    best_match = decision.best_match
    if best_match is None:
        return None
    for diagnostic in decision.diagnostics:
        if diagnostic.query != best_match.query:
            continue
        if diagnostic.row_index != best_match.row_index:
            continue
        return diagnostic
    return None


def _match_log_header_lines(item: Item, decision: MatchDecision) -> list[str]:
    """Return the static header lines for one item matching log."""
    return [
        f"item_code={item.code}",
        f"item_name={item.name}",
        f"item_qty={item.qty}",
        f"final_reason={decision.final_reason}",
        f"best_match_query={decision.best_match.query if decision.best_match else ''}",
        f"best_match_row_index={decision.best_match.row_index if decision.best_match else ''}",
        f"best_match_score={decision.best_match.score if decision.best_match else ''}",
        "",
        "candidates:",
    ]


def candidate_log_lines(
    candidate_index: int,
    diagnostic: CandidateMatchDiagnostic,
) -> list[str]:
    """Build the log lines for one candidate considered during matching."""
    breakdown = diagnostic.breakdown
    candidate_names = candidate_name_fields(diagnostic)
    lines = _candidate_identity_lines(candidate_index, diagnostic, candidate_names)
    lines.extend(
        _candidate_score_lines(diagnostic, breakdown)
    )
    return lines


def _candidate_identity_lines(
    candidate_index: int,
    diagnostic: CandidateMatchDiagnostic,
    candidate_names: dict[str, str],
) -> list[str]:
    """Return the identity and availability lines for one candidate log block."""
    return [
        f"- candidate_{candidate_index}:",
        f"  query={diagnostic.query}",
        f"  row_index={diagnostic.row_index}",
        f"  product_name_en={candidate_names['product_name_en']}",
        f"  product_name_ar={candidate_names['product_name_ar']}",
        f"  available_quantity={diagnostic.candidate.get('availableQuantity')}",
        f"  products_count={diagnostic.candidate.get('productsCount')}",
        f"  store_product_id={diagnostic.candidate.get('storeProductId')}",
    ]


def _candidate_score_lines(
    diagnostic: CandidateMatchDiagnostic,
    breakdown,
) -> list[str]:
    """Return the score and acceptance lines for one candidate log block."""
    return [
        f"  total_score={diagnostic.score:.3f}",
        f"  sequence_score={breakdown.sequence_score:.3f}",
        f"  overlap_score={breakdown.overlap_score:.3f}",
        f"  numeric_overlap={breakdown.numeric_overlap:.3f}",
        f"  exact_bonus={breakdown.exact_bonus:.3f}",
        f"  availability_bonus={breakdown.availability_bonus:.3f}",
        f"  sort_key={diagnostic.sort_key}",
        f"  accepted={diagnostic.accepted}",
        f"  accepted_reason={diagnostic.accepted_reason}",
        f"  rejection_reason={diagnostic.rejection_reason}",
        "",
    ]


def match_log_csv_rows(item: Item, decision: MatchDecision) -> list[dict[str, object]]:
    """Build CSV rows for all candidates considered during item matching."""
    rows: list[dict[str, object]] = []
    for rank, diagnostic in enumerate(_sorted_diagnostics(decision), start=1):
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
        "best_match_row_index": decision.best_match.row_index if decision.best_match else "",
        "best_match_score": decision.best_match.score if decision.best_match else "",
    }


def _score_csv_fields(diagnostic: CandidateMatchDiagnostic, breakdown) -> dict[str, object]:
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


def candidate_name_fields(diagnostic: CandidateMatchDiagnostic) -> dict[str, str]:
    """Return the English and Arabic candidate names for one diagnostic."""
    return {
        "product_name_en": str(diagnostic.candidate.get("productNameEn") or ""),
        "product_name_ar": str(diagnostic.candidate.get("productName") or ""),
    }


def accepted_product_name(decision: MatchDecision) -> str:
    """Return the accepted product name when a best match exists."""
    if not decision.best_match:
        return ""
    candidate = decision.best_match.data
    return str(candidate.get("productNameEn") or candidate.get("productName") or "")


def safe_item_label(item: Item) -> str:
    """Return a filesystem-safe label for item-specific artifacts."""
    item_code = str(item.code or "no_code").strip().replace(" ", "_")
    safe_label = "".join(
        character
        for character in item_code
        if character.isalnum() or character in {"_", "-"}
    )
    return safe_label or "no_code"


def match_log_section_separator(item: Item) -> str:
    """Return the section separator used inside the aggregated match log."""
    return (
        "\n"
        + "=" * 80
        + "\n"
        + f"item_code={item.code} | item_name={item.name}\n"
        + "=" * 80
        + "\n"
    )


def _sorted_diagnostics(decision: MatchDecision) -> list[CandidateMatchDiagnostic]:
    """Return candidate diagnostics sorted from best to worst match."""
    return sorted(decision.diagnostics, key=lambda current: current.sort_key, reverse=True)
