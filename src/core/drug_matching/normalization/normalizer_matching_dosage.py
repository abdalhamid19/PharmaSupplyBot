"""Dosage matching logic for drug components."""

from __future__ import annotations

from .normalizer_matching_dosage_core import _dosage_match_check
from .normalizer_matching_dosage_compatibility import (
    _dosage_compatible,
    _matching_canonical_dosage,
    _canonical_dosage_values_mg,
    _canonical_dosage_value_mg,
    _concor_plus_dosage_compatible,
    _liquid_total_matches_per_5,
    _single_per_5_matches_total,
    _summed_combo_matches_single,
    _liquid_primary_strength_matches,
)


__all__ = [
    "_dosage_match_check",
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
