"""Helper functions for Tawreed product matching logs."""

from __future__ import annotations

from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision
from ..core.utils.excel import Item

MAX_DETAILED_MATCH_CANDIDATES = 25


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
