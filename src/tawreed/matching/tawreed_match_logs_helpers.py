"""Helper functions for Tawreed match logs."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision
from ..core.utils.excel import Item


@dataclass(frozen=True)
class OrderResultSummary:
    """One compact execution summary row for an item processed during ordering."""

    status: str
    reason: str
    ordered_total_qty: int = 0
    matched_product_english_name: str = ""
    matched_product_english_name_source: str = ""
    matched_product_arabic_name: str = ""
    matched_query: str = ""
    selected_discount_percent: str = ""
    selected_store_name: str = ""
    searched_queries_count: int = 0
    searched_queries: str = ""
    elapsed_seconds: float = 0.0
    match_elapsed_seconds: float = 0.0
    timing_seconds: dict[str, float] | None = None


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


def sorted_diagnostics(decision: MatchDecision) -> list[CandidateMatchDiagnostic]:
    """Return all candidate diagnostics sorted from best to worst match."""
    return sorted(
        decision.diagnostics, key=lambda current: current.sort_key, reverse=True
    )


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


__all__ = [
    "OrderResultSummary",
    "candidate_name_fields",
    "accepted_product_name",
    "safe_item_label",
    "match_log_section_separator",
    "sorted_diagnostics",
    "should_write_detailed_match_log",
    "_best_match_diagnostic",
]
