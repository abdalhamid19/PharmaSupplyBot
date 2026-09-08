"""Strict, source-independent medicine form, strength, and pack checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


_FORMS = {
    "TABLET": ("TAB", "TABS", "TABLET", "TABLETS", "\u0642\u0631\u0635", "\u0623\u0642\u0631\u0627\u0635", "\u0627\u0642\u0631\u0627\u0635"),
    "CAPSULE": ("CAP", "CAPS", "CAPSULE", "CAPSULES", "\u0643\u0628\u0633\u0648\u0644", "\u0643\u0628\u0633\u0648\u0644\u0629", "\u0643\u0628\u0633\u0648\u0644\u0627\u062a"),
    "FILM": ("FILM", "FILMS", "FLIM", "FLIMS", "\u0641\u064a\u0644\u0645", "\u0641\u064a\u0644\u0645\u0633"),
    "SYRUP": ("SYRUP", "\u0634\u0631\u0627\u0628"),
    "CREAM": ("CREAM", "\u0643\u0631\u064a\u0645"),
    "OINTMENT": ("OINT", "OINTMENT", "\u0645\u0631\u0647\u0645"),
    "GEL": ("GEL", "\u062c\u0644", "\u062c\u064a\u0644"),
    "INJECTION": ("INJ", "INJECTION", "\u062d\u0642\u0646", "\u0627\u0645\u0628\u0648\u0644", "\u0623\u0645\u0628\u0648\u0644"),
    "DROPS": ("DROP", "DROPS", "\u0642\u0637\u0631\u0629", "\u0642\u0637\u0631\u0627\u062a"),
    "SPRAY": ("SPRAY", "\u0628\u062e\u0627\u062e", "\u0633\u0628\u0631\u0627\u0649", "\u0633\u0628\u0631\u0627\u064a"),
    "SACHET": ("SACHET", "SACHETS", "\u0643\u064a\u0633", "\u0627\u0643\u064a\u0627\u0633", "\u0623\u0643\u064a\u0627\u0633"),
}
_STRENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mcg|µg|ug|mg|gm|g|ml|iu|%)|"
    r"(\d+(?:\.\d+)?)\s*(\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645|\u0645\u062c\u0645|\u0645\u0644\u062c\u0645|\u062c\u0631\u0627\u0645|\u062c\u0645|\u0645\u0644|\u0648\u062d\u062f\u0629|%)",
    re.IGNORECASE,
)
_PACK_RE = re.compile(
    r"\b(\d+)\s*(?:tab|tabs|tablet|tablets|cap|caps|capsule|capsules|film|films|flim|flims)\b|"
    r"(\d+)\s*(?:\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u064a\u0633|\u0627\u0643\u064a\u0627\u0633|\u0623\u0643\u064a\u0627\u0633|\u0641\u064a\u0644\u0645|\u0641\u064a\u0644\u0645\u0633)",
    re.IGNORECASE,
)
_PACK_AFTER_FORM_RE = re.compile(
    r"\b(?:tab|tabs|tablet|tablets|cap|caps|capsule|capsules|film|films|flim|flims)\s*(\d+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CanonicalStrength:
    value: float
    unit: str


@dataclass(frozen=True)
class ProductAttributes:
    forms: frozenset[str]
    strengths: frozenset[CanonicalStrength]
    packs: frozenset[int]


@dataclass(frozen=True)
class CompatibilityResult:
    accepted: bool
    query: ProductAttributes
    candidate: ProductAttributes
    rejection_reason: str = ""


def extract_product_attributes(text: str) -> ProductAttributes:
    """Extract only explicit product-variant attributes from Arabic or English text."""
    normalized = _normalize_attribute_text(text)
    forms = {
        canonical
        for canonical, aliases in _FORMS.items()
        if any(_has_alias(normalized, alias.casefold()) for alias in aliases)
    }
    strengths = {
        _canonical_strength(match)
        for match in _STRENGTH_RE.finditer(normalized)
    }
    packs = {
        int(match.group(1) or match.group(2))
        for match in _PACK_RE.finditer(normalized)
    }
    packs.update(int(match.group(1)) for match in _PACK_AFTER_FORM_RE.finditer(normalized))
    return ProductAttributes(frozenset(forms), frozenset(strengths), frozenset(packs))


def _normalize_attribute_text(text: str) -> str:
    """Normalize documented supplier typos without changing brand tokens."""
    normalized = (text or "").casefold()
    return re.sub(r"(?<![a-z])mgc(?![a-z])", "mcg", normalized)


def validate_product_compatibility(query: str, candidate: str) -> CompatibilityResult:
    """Require every explicit order attribute to be proven by the candidate."""
    query_attributes = extract_product_attributes(query)
    candidate_attributes = extract_product_attributes(candidate)
    rejection = _mismatch_reason(query_attributes, candidate_attributes)
    return CompatibilityResult(
        accepted=not rejection,
        query=query_attributes,
        candidate=candidate_attributes,
        rejection_reason=rejection,
    )


def _has_alias(text: str, alias: str) -> bool:
    if alias.isascii():
        return bool(re.search(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE))
    return alias in text


def _canonical_strength(match: re.Match[str]) -> CanonicalStrength:
    value = float(match.group(1) or match.group(3))
    raw_unit = (match.group(2) or match.group(4) or "").casefold()
    unit = {
        "mcg": "mcg", "µg": "mcg", "ug": "mcg", "\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645": "mcg",
        "mg": "mg", "\u0645\u062c\u0645": "mg", "\u0645\u0644\u062c\u0645": "mg",
        "g": "mg", "gm": "mg", "\u062c\u0631\u0627\u0645": "mg", "\u062c\u0645": "mg",
        "ml": "ml", "\u0645\u0644": "ml", "iu": "iu", "\u0648\u062d\u062f\u0629": "iu", "%": "%",
    }[raw_unit]
    if raw_unit in {"g", "gm", "\u062c\u0631\u0627\u0645", "\u062c\u0645"}:
        value *= 1000
    return CanonicalStrength(value, unit)


def _mismatch_reason(query: ProductAttributes, candidate: ProductAttributes) -> str:
    if query.forms and not candidate.forms:
        return "candidate form is not proven"
    if query.forms and not (query.forms & candidate.forms):
        return "candidate form conflicts with requested form"
    if query.strengths and not candidate.strengths:
        return "candidate strength is not proven"
    if query.strengths and not (query.strengths & candidate.strengths):
        return "candidate strength conflicts with requested strength"
    if not query.strengths and candidate.strengths:
        return "candidate has an unrequested strength"
    if query.packs and not candidate.packs:
        return "candidate pack is not proven"
    if query.packs and not (query.packs & candidate.packs):
        return "candidate pack conflicts with requested pack"
    return ""


__all__ = [
    "CanonicalStrength",
    "CompatibilityResult",
    "ProductAttributes",
    "extract_product_attributes",
    "validate_product_compatibility",
]
