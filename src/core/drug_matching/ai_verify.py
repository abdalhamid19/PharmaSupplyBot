"""AI verification logic for drug matching."""

from __future__ import annotations

from .ai_verify_main import run_ai_verification
from .ai_verify_selection import _select_for_verification, _build_verify_items
from .ai_verify_handlers import _handle_rejected
from .ai_verify_helpers import (
    _internal_value,
    _set_internal_matched_price,
    _trace_api_attempts,
    _trace_parse_failure,
    _trace_skip_all_verify,
    _apply_correction,
    _clear_match,
    _FUZZY_VERIFY_METHODS,
)
from .ai_verify_batch import _batch_verify, _apply_verification


# Export helper functions for use by ai_review.py
__all__ = [
    "run_ai_verification",
    "_internal_value",
    "_set_internal_matched_price",
    "_trace_api_attempts",
    "_trace_parse_failure",
    "_trace_skip_all_verify",
    "_apply_correction",
    "_clear_match",
    "_FUZZY_VERIFY_METHODS",
    "_select_for_verification",
    "_build_verify_items",
    "_handle_rejected",
    "_batch_verify",
    "_apply_verification",
]
