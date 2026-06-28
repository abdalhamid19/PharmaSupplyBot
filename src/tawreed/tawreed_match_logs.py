"""Diagnostic log builders for Tawreed product matching."""

from __future__ import annotations

from ..core.matching_models import MatchDecision
from ..core.utils.excel import Item
from .tawreed_match_logs_models import OrderResultSummary
from .tawreed_match_logs_main import write_match_log, append_order_result_summary


# Backward compatibility: redirect to refactored modules
def match_log_content(item: Item, decision: MatchDecision) -> str:
    from .tawreed_match_logs_content import match_log_content as _fn
    return _fn(item, decision)


def candidate_log_lines(candidate_index: int, diagnostic):
    from .tawreed_match_logs_content import candidate_log_lines as _fn
    return _fn(candidate_index, diagnostic)


def match_log_csv_rows(item: Item, decision: MatchDecision):
    from .tawreed_match_logs_csv import match_log_csv_rows as _fn
    return _fn(item, decision)


def candidate_name_fields(diagnostic):
    from .tawreed_match_logs_helpers import candidate_name_fields as _fn
    return _fn(diagnostic)


def accepted_product_name(decision: MatchDecision):
    from .tawreed_match_logs_helpers import accepted_product_name as _fn
    return _fn(decision)


def safe_item_label(item: Item):
    from .tawreed_match_logs_helpers import safe_item_label as _fn
    return _fn(item)


def match_log_section_separator(item: Item):
    from .tawreed_match_logs_helpers import match_log_section_separator as _fn
    return _fn(item)


def sorted_diagnostics(decision: MatchDecision):
    from .tawreed_match_logs_helpers import sorted_diagnostics as _fn
    return _fn(decision)


def should_write_detailed_match_log(decision: MatchDecision):
    from .tawreed_match_logs_decision import should_write_detailed_match_log as _fn
    return _fn(decision)


def _best_match_diagnostic(decision: MatchDecision):
    from .tawreed_match_logs_decision import _best_match_diagnostic as _fn
    return _fn(decision)


def _match_log_header_lines(item: Item, decision: MatchDecision):
    from .tawreed_match_logs_content import _match_log_header_lines as _fn
    return _fn(item, decision)


def _candidate_identity_lines(candidate_index: int, diagnostic, candidate_names):
    from .tawreed_match_logs_content import _candidate_identity_lines as _fn
    return _fn(candidate_index, diagnostic, candidate_names)


def _candidate_score_lines(diagnostic, breakdown):
    from .tawreed_match_logs_content import _candidate_score_lines as _fn
    return _fn(diagnostic, breakdown)


def _match_log_csv_row(item: Item, decision: MatchDecision, diagnostic, rank: int):
    from .tawreed_match_logs_csv import _match_log_csv_row as _fn
    return _fn(item, decision, diagnostic, rank)


def _shared_csv_fields(item: Item, decision: MatchDecision, diagnostic, rank: int):
    from .tawreed_match_logs_csv import _shared_csv_fields as _fn
    return _fn(item, decision, diagnostic, rank)


def _item_and_candidate_csv_fields(item: Item, decision: MatchDecision, diagnostic, rank: int):
    from .tawreed_match_logs_csv import _item_and_candidate_csv_fields as _fn
    return _fn(item, decision, diagnostic, rank)


def _candidate_csv_fields(diagnostic):
    from .tawreed_match_logs_csv import _candidate_csv_fields as _fn
    return _fn(diagnostic)


def _best_match_csv_fields(decision: MatchDecision):
    from .tawreed_match_logs_csv import _best_match_csv_fields as _fn
    return _fn(decision)


def _score_csv_fields(diagnostic, breakdown):
    from .tawreed_match_logs_csv import _score_csv_fields as _fn
    return _fn(diagnostic, breakdown)


__all__ = [
    "OrderResultSummary",
    "write_match_log",
    "append_order_result_summary",
    "match_log_content",
    "candidate_log_lines",
    "match_log_csv_rows",
    "candidate_name_fields",
    "accepted_product_name",
    "safe_item_label",
    "match_log_section_separator",
    "sorted_diagnostics",
    "should_write_detailed_match_log",
    "_best_match_diagnostic",
    "_match_log_header_lines",
    "_candidate_identity_lines",
    "_candidate_score_lines",
    "_match_log_csv_row",
    "_shared_csv_fields",
    "_item_and_candidate_csv_fields",
    "_candidate_csv_fields",
    "_best_match_csv_fields",
    "_score_csv_fields",
]
