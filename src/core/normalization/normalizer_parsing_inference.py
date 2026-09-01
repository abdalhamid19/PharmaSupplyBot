"""Dosage inference and helper functions for parsing."""

from __future__ import annotations

import re
from .normalizer_parsing_constants import (
    FORM_PREFIXES, FORM_WORDS, NOISE_WORDS, BRAND_QUALIFIERS,
    SOFT_BRAND_DESCRIPTORS, CONNECTOR_WORDS, FLAVOR_WORDS, SUPPLEMENT_WORDS,
    INFUSION_CONTEXT_WORDS,
)


def _infer_missing_dosage(norm, qty, volume, weight, form):
    slash = re.search(r"\b\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\b", norm)
    if slash:
        return (re.sub(r"\s+", "", slash.group(0)),), ("MG",)
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", norm)
    consumed = [v for v in (qty, volume, weight) if v]
    remaining = []
    for num in nums:
        normalized = _canonical_number(num)
        consumed_idx = next((i for i, v in enumerate(consumed) if _canonical_number(v) == normalized), None)
        if consumed_idx is not None:
            consumed.pop(consumed_idx)
        else:
            remaining.append(normalized)
    if len(remaining) != 1:
        return (), ()
    if qty or form in {"TAB", "CAP", "SUPP", "AMP", "VIAL", "SPRAY"} or (volume and form in {"SYRUP", "SUSP"}):
        return (remaining[0],), ("MG",)
    return (), ()


def _is_brand_boundary(words, idx):
    from .normalizer_parsing_constants import (
        FORM_PREFIXES,
        FORM_WORDS,
        NOISE_WORDS,
        BRAND_QUALIFIERS,
        SOFT_BRAND_DESCRIPTORS,
        CONNECTOR_WORDS,
        FLAVOR_WORDS,
        SUPPLEMENT_WORDS,
    )
    word = words[idx]
    hard = {FORM_PREFIXES, FORM_WORDS, NOISE_WORDS, BRAND_QUALIFIERS}
    soft = {SOFT_BRAND_DESCRIPTORS, CONNECTOR_WORDS, FLAVOR_WORDS, SUPPLEMENT_WORDS}
    if word in set().union(*hard):
        return True
    if _is_pediatric_inf(words, idx) or _is_descriptive_brand_word(word):
        return True
    return idx > 0 and word in set().union(*soft)


def _canonical_number(value):
    return str(float(value)).rstrip("0").rstrip(".") if "." in value else value


def _weight_is_strength(weight, form, words):
    if not weight:
        return False
    if form == "TAB" and words & {"EFF", "EFFERVESCENT"}:
        return True
    return form in {"VIAL", "AMP"} or bool(words & INFUSION_CONTEXT_WORDS)


def _is_pediatric_inf(words, idx):
    if words[idx] != "INF" or idx == 0:
        return False
    return not bool(set(words) & INFUSION_CONTEXT_WORDS)


def _is_descriptive_brand_word(word):
    return word in {"GELATIN"}
