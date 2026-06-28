"""Decision logic and diagnostics for product matching."""

from __future__ import annotations

from .product_matching_decisions_main import (
    _decision_from_diagnostics,
    _empty_match_decision,
    _rejected_match_decision,
    _accepted_match_decision,
    _best_accepted_diagnostic,
    _accepted_ambiguity_reason,
    _tied_accepted_ids,
    _rejected_decision_reason,
    _accepted_decision_reason,
    _search_match,
)
from .product_matching_decisions_builders import (
    _build_candidate_diagnostics,
    _apply_top_k_checks,
    _candidate_diagnostic,
)
from .product_matching_decisions_diagnostics import (
    _diagnostic_record,
    _rejected_diagnostic,
)


__all__ = [
    "_decision_from_diagnostics",
    "_empty_match_decision",
    "_rejected_match_decision",
    "_accepted_match_decision",
    "_best_accepted_diagnostic",
    "_accepted_ambiguity_reason",
    "_tied_accepted_ids",
    "_rejected_decision_reason",
    "_accepted_decision_reason",
    "_search_match",
    "_build_candidate_diagnostics",
    "_apply_top_k_checks",
    "_candidate_diagnostic",
    "_diagnostic_record",
    "_rejected_diagnostic",
]
