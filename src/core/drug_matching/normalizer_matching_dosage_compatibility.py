"""Dosage compatibility checking functions."""

from __future__ import annotations

from .normalizer_parsing import DrugComponents
from .normalizer_constants import LIQUID_DOSE_FORMS
from .normalizer_matching_numeric import _dosage_parts


def _dosage_compatible(d: DrugComponents, m: DrugComponents) -> bool:
    """Check if dosages are compatible."""
    canonical = _matching_canonical_dosage(d, m)
    if canonical is not None:
        return canonical
    d_parts = _dosage_parts(d.dosage_nums)
    m_parts = _dosage_parts(m.dosage_nums)
    if _concor_plus_dosage_compatible(d_parts, m_parts, d, m):
        return True
    if tuple(sorted(d_parts, key=float)) == tuple(sorted(m_parts, key=float)):
        return True
    if _summed_combo_matches_single(d_parts, m_parts):
        return True
    if _liquid_total_matches_per_5(d_parts, m_parts, d, m):
        return True
    return _liquid_primary_strength_matches(d_parts, m_parts, d, m)


def _matching_canonical_dosage(d: DrugComponents, m: DrugComponents):
    """Check if canonical dosage values match."""
    left = _canonical_dosage_values_mg(d)
    right = _canonical_dosage_values_mg(m)
    if not left or not right:
        return None
    return tuple(sorted(left)) == tuple(sorted(right))


def _canonical_dosage_values_mg(c: DrugComponents) -> tuple:
    """Convert dosage values to canonical mg units."""
    if len(c.dosage_nums) != len(c.dosage_units):
        return ()
    values = []
    for num, unit in zip(c.dosage_nums, c.dosage_units):
        value = _canonical_dosage_value_mg(num, unit)
        if value is None:
            return ()
        values.append(value)
    return tuple(values)


def _canonical_dosage_value_mg(num: str, unit: str):
    """Convert single dosage value to mg."""
    if "/" in num:
        return None
    value = float(num)
    normalized_unit = unit.replace(" ", "").upper()
    if normalized_unit in {"GM", "G"}:
        return value * 1000.0
    if normalized_unit == "MG":
        return value
    if normalized_unit == "MCG":
        return value / 1000.0
    return None


def _concor_plus_dosage_compatible(left, right, d: DrugComponents, m: DrugComponents) -> bool:
    """Special case for Concor Plus dosage compatibility."""
    words = set(d.normalized.split()) | set(m.normalized.split())
    if not {"CONCOR", "PLUS"} <= words:
        return False
    if not left or not right:
        return False
    return left[0] == right[0]


def _liquid_total_matches_per_5(left, right, d: DrugComponents, m: DrugComponents) -> bool:
    """Check if liquid dosage matches per 5ml."""
    forms = {d.form, m.form}
    if not forms & LIQUID_DOSE_FORMS:
        return False
    try:
        if len(left) == 1 and len(right) == 2:
            return _single_per_5_matches_total(left[0], right[0], right[1], m.volume)
        if len(right) == 1 and len(left) == 2:
            return _single_per_5_matches_total(right[0], left[0], left[1], d.volume)
    except ValueError:
        return False
    return False


def _single_per_5_matches_total(single, total, total_volume, parsed_volume) -> bool:
    """Check if single dose matches total per 5ml."""
    from .normalizer_matching_numeric import _canonical_number
    if parsed_volume and _canonical_number(parsed_volume) != _canonical_number(total_volume):
        return False
    return abs((float(total) / float(total_volume)) - (float(single) / 5.0)) <= 0.01


def _summed_combo_matches_single(left, right) -> bool:
    """Check if summed combo matches single dose."""
    if len(left) <= 1 and len(right) <= 1:
        return False
    try:
        left_vals = [float(v) for v in left]
        right_vals = [float(v) for v in right]
    except ValueError:
        return False
    if len(left_vals) > 1 and len(right_vals) == 1:
        return abs(sum(left_vals) - right_vals[0]) <= 0.01
    if len(right_vals) > 1 and len(left_vals) == 1:
        return abs(sum(right_vals) - left_vals[0]) <= 0.01
    return False


def _liquid_primary_strength_matches(d_parts, m_parts, d: DrugComponents, m: DrugComponents) -> bool:
    """Check if liquid primary strength matches."""
    if not ({d.form, m.form} & LIQUID_DOSE_FORMS):
        return False
    return (len(d_parts) == 1 and len(m_parts) > 1 and d_parts[0] == m_parts[0]) or (len(m_parts) == 1 and len(d_parts) > 1 and m_parts[0] == d_parts[0])


__all__ = [
    "_dosage_compatible",
    "_matching_canonical_dosage",
    "_canonical_dosage_values_mg",
    "_canonical_dosage_value_mg",
    "_concor_plus_dosage_compatible",
    "_liquid_total_matches_per_5",
    "_single_per_5_matches_total",
    "_summed_combo_matches_single",
    "_liquid_primary_strength_matches",
]
