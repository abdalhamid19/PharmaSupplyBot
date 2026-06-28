"""Log content building for Tawreed product matching."""

from __future__ import annotations

from ..core.matching_types import CandidateMatchDiagnostic, MatchDecision
from ..core.utils.excel import Item
from .tawreed_match_logs_helpers import (
    MAX_DETAILED_MATCH_CANDIDATES,
    sorted_diagnostics,
)


def match_log_content(item: Item, decision: MatchDecision) -> str:
    """Build the detailed product-matching log content for one item."""
    from .tawreed_match_logs_helpers import candidate_name_fields
    lines = _match_log_header_lines(item, decision)
    for candidate_index, diagnostic in enumerate(
        sorted_diagnostics(decision)[:MAX_DETAILED_MATCH_CANDIDATES], start=1
    ):
        lines.extend(candidate_log_lines(candidate_index, diagnostic))
    return "\n".join(lines) + "\n"


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
    from .tawreed_match_logs_helpers import candidate_name_fields
    breakdown = diagnostic.breakdown
    candidate_names = candidate_name_fields(diagnostic)
    lines = _candidate_identity_lines(candidate_index, diagnostic, candidate_names)
    lines.extend(_candidate_score_lines(diagnostic, breakdown))
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
