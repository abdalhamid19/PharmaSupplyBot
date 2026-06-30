"""Helper functions for drug component matching."""

import re
from .normalizer_parsing import DrugComponents
from .normalizer_constants import (
    ADULT_WORDS, BABY_FORMULA_MODIFIERS, CRITICAL_CHEMICALS,
    CRITICAL_MODIFIERS, FLAVOR_WORDS, INFUSION_CONTEXT_WORDS,
    PEDIATRIC_WORDS, ROUTE_WORDS, VITAMIN_MODIFIERS, COLOR_WORDS
)


def _has_reliable_english_name(c: DrugComponents) -> bool:
    """Check if component has reliable English name."""
    if c.is_synthetic:
        return False
    text = c.normalized or ""
    return any(char.isalpha() and char.isascii() for char in text)


def _modifier_is_optional(modifier, d_words, m_words):
    """Check if modifier is optional based on context."""
    combined = d_words | m_words
    nasal = {"SPRAY", "SPRAYS", "DOSES", "DROPS", "DROP", "EYE"}
    vaginal = {"SUPP", "SUPPS", "CAP", "CAPS", "CAPSULE", "CAPSULES"}

    optional_rules = {
        "ADVANCE": "MILK" in d_words and "MILK" in m_words,
        "EXTRA": "EMOLLIENT" in d_words or "EMOLLIENT" in m_words,
        "NASAL": nasal & d_words and nasal & m_words,
        "VAGINAL": vaginal & d_words and vaginal & m_words,
        "R": "PROLONGED" in combined,
        "SR": "RETARD" in combined,
        "MOUTH": ("MOUTHWASH" in d_words or "MOUTHWASH" in m_words)
        and ("WASH" in d_words or "WASH" in m_words),
    }
    return optional_rules.get(modifier, False)


def _insulin_variant_signature(c: DrugComponents) -> frozenset:
    """Extract insulin variant signature from component."""
    if "INSULINAGYPT" not in c.normalized.replace(" ", ""):
        return frozenset()
    words = set(c.normalized.split())
    variants = set(words & {"N", "R"})
    if re.search(r"\b70\s*/\s*30\b", c.normalized):
        variants.add("70/30")
    return frozenset(variants)


def _variant_tokens(c: DrugComponents) -> frozenset:
    """Extract variant tokens (flavor/color) from component."""
    words = set(c.normalized.split())
    return frozenset(words & (FLAVOR_WORDS | COLOR_WORDS))


def _has_pediatric_signal(words) -> bool:
    """Check if words contain pediatric signal."""
    if words & PEDIATRIC_WORDS:
        return True
    if "INF" not in words:
        return False
    return not bool(words & INFUSION_CONTEXT_WORDS)


def _has_adult_signal(words) -> bool:
    """Check if words contain adult signal."""
    return bool(words & ADULT_WORDS)


def _route_signals(words) -> frozenset:
    """Extract route signals from words."""
    routes = set(words & ROUTE_WORDS)
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return frozenset(routes)


__all__ = [
    "_has_reliable_english_name",
    "_modifier_is_optional",
    "_insulin_variant_signature",
    "_variant_tokens",
    "_has_pediatric_signal",
    "_has_adult_signal",
    "_route_signals",
]
