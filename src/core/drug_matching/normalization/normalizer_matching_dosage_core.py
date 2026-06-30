"""Core dosage matching check functions."""

from __future__ import annotations

from .normalizer_parsing import DrugComponents
from .normalizer_matching_helpers import _has_reliable_english_name
from .normalizer_matching_numeric import (
    _component_numeric_signals,
    _numeric_signals_match_dosage,
    _has_stage_mismatch,
)


def _dosage_match_check(d: DrugComponents, m: DrugComponents) -> tuple[bool, str]:
    """Check if dosages match between two components."""
    dosage_checked_compatible = False
    if d.dosage_nums and m.dosage_nums:
        from .normalizer_matching_dosage_compatibility import _dosage_compatible
        if not _dosage_compatible(d, m):
            return False, "different_dosage"
        dosage_checked_compatible = True
    if not dosage_checked_compatible:
        if _has_reliable_english_name(d) and _has_reliable_english_name(m):
            d_numeric = _component_numeric_signals(d)
            m_numeric = _component_numeric_signals(m)
            d_matched_dosage = False
            m_matched_dosage = False
            if d_numeric and m.dosage_nums:
                if _numeric_signals_match_dosage(d_numeric, m.dosage_nums):
                    d_matched_dosage = True
                else:
                    return False, "different_dosage"
            if m_numeric and d.dosage_nums:
                if _numeric_signals_match_dosage(m_numeric, d.dosage_nums):
                    m_matched_dosage = True
                else:
                    return False, "different_dosage"
            if d.product_class == "baby_food" or m.product_class == "baby_food":
                if _has_stage_mismatch(d_numeric, m_numeric):
                    return False, "different_baby_formula_stage"
            if d_numeric and m_numeric and d_numeric != m_numeric and not d_matched_dosage and not m_matched_dosage:
                return False, "different_dosage"
    return True, "ok"


__all__ = ["_dosage_match_check"]
