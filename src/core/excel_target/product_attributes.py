"""Strict, source-independent medicine form, strength, and pack checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


_FORMS = {
    "TABLET": ("TAB", "TABS", "TABLET", "TABLETS", "\u0642\u0631\u0635", "\u0623\u0642\u0631\u0627\u0635", "\u0627\u0642\u0631\u0627\u0635"),
    "CAPSULE": ("CAP", "CAPS", "CAPSULE", "CAPSULES", "\u0643\u0628\u0633\u0648\u0644", "\u0643\u0628\u0633\u0648\u0644\u0629", "\u0643\u0628\u0633\u0648\u0644\u0627\u062a"),
    "FILM": ("FILM", "FILMS", "FLIM", "FLIMS", "\u0641\u064a\u0644\u0645", "\u0641\u064a\u0644\u0645\u0633"),
    "SYRUP": ("SYRUP", "\u0634\u0631\u0627\u0628"),
    "CREAM": ("CREAM", "\u0643\u0631\u064a\u0645"),
    "OINTMENT": ("OINT", "OINTMENT", "\u0645\u0631\u0647\u0645"),
    "GEL": ("GEL", "\u062c\u0644", "\u062c\u064a\u0644"),
    "SUSPENSION": ("SUSP", "SUSPENSION", "\u0645\u0639\u0644\u0642", "\u0645\u0639\u0644\u0642\u0629", "\u0645\u0639\u0644\u0642\u0627\u062a"),
    "SOLUTION": ("SOL", "SOLN", "SOLUTION", "\u0645\u062d\u0644\u0648\u0644"),
    "LOTION": ("LOTION", "\u0644\u0648\u0634\u0646"),
    "VIAL": ("VIAL", "VIALS", "\u0641\u064a\u0627\u0644", "\u0642\u0627\u0631\u0648\u0631\u0629"),
    "AMPOULE": ("AMP", "AMPS", "AMPOULE", "AMPOULES", "\u0627\u0645\u0628\u0648\u0644", "\u0645\u0628\u0648\u0644", "\u0623\u0645\u0628\u0648\u0644", "\u0627\u0645\u0628\u0648\u0644\u0629", "\u0623\u0645\u0628\u0648\u0644\u0629", "\u0627\u0645\u0628\u0648\u0644\u0627\u062a", "\u0623\u0645\u0628\u0648\u0644\u0627\u062a"),
    "SUPPOSITORY": ("SUPP", "SUPPOSITORY", "SUPPOSITORIES", "\u0644\u0628\u0648\u0633", "\u062a\u062d\u0627\u0645\u064a\u0644", "\u062a\u062d\u0645\u064a\u0644\u0629"),
    "LOZENGE": ("LOZENGE", "LOZENGES", "\u0627\u0633\u062a\u062d\u0644\u0627\u0628"),
    "POWDER": ("POWDER", "POWDERS", "\u0628\u0648\u062f\u0631\u0629", "\u0628\u0648\u062f\u0631\u0647", "\u0645\u0633\u062d\u0648\u0642"),
    "INJECTION": ("INJ", "INJECTION", "\u062d\u0642\u0646"),
    "DROPS": ("DROP", "DROPS", "\u0642\u0637\u0631\u0629", "\u0642\u0637\u0631\u0627\u062a", "\u0642\u0637\u0631\u0647", "\u0646\u0642\u0637"),
    "SPRAY": ("SPRAY", "\u0628\u062e\u0627\u062e", "\u0633\u0628\u0631\u0627\u0649", "\u0633\u0628\u0631\u0627\u064a"),
    "SACHET": ("SACHET", "SACHETS", "\u0643\u064a\u0633", "\u0627\u0643\u064a\u0627\u0633", "\u0623\u0643\u064a\u0627\u0633"),
    # ``AM`` is an ambiguous supplier abbreviation. Keep it distinct from
    # ``AMPOULE`` so it cannot silently authorize a different presentation.
    "AMBIGUOUS_AM": ("AM",),
    "GUMMY": ("GUMMY", "GUMMIES", "\u062c\u0627\u0645\u064a\u0632", "\u062c\u0627\u0645\u064a"),
}
_STRENGTH_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mcg|µg|ug|mg|gm|g|ml|iu|%)(?![a-z])|"
    r"(\d+(?:\.\d+)?)\s*(\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645|\u0645\u062c\u0645|\u0645\u0644\u062c\u0645|\u062c\u0631\u0627\u0645|\u062c\u0645|\u0645\u0644|\u0648\u062d\u062f\u0629|%)",
    re.IGNORECASE,
)
_NUMBER = r"\d+(?:\.\d+)?"
_UNIT = (
    r"(?:mcg|µg|ug|mg|gm|g|ml|iu|%|"
    r"\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645|\u0645\u062c\u0645|\u0645\u0644\u062c\u0645|"
    r"\u062c\u0631\u0627\u0645|\u062c\u0645|\u0645\u0644|\u0648\u062d\u062f\u0629)"
)
_COMPOUND_RE = re.compile(
    rf"(?<![\w.])(?P<expression>{_NUMBER}\s*(?:{_UNIT})?"
    rf"(?:\s*/\s*{_NUMBER}\s*(?:{_UNIT})?)+)(?![\w.])",
    re.IGNORECASE,
)
_COMPOUND_PART_RE = re.compile(
    rf"(?P<number>{_NUMBER})\s*(?P<unit>{_UNIT})?\Z",
    re.IGNORECASE,
)
_BARE_DROPS_DOSE_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:oral\s+)?(?:drops?|\u0646\u0642\u0637|\u0642\u0637\u0631\u0629|\u0642\u0637\u0631\u0627\u062a|\u0642\u0637\u0631\u0647)(?![\w])",
    re.IGNORECASE,
)
_PACK_RE = re.compile(
    r"\b(\d+)\s*(?:tab|tabs|tablet|tablets|cap|caps|capsule|capsules|film|films|flim|flims|vial|vials|amp|amps|ampoule|ampoules|supp|suppository|suppositories|lozenge|lozenges|gummy|gummies)\b|"
    r"(\d+)\s*(?:\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u064a\u0633|\u0627\u0643\u064a\u0627\u0633|\u0623\u0643\u064a\u0627\u0633|\u0641\u064a\u0644\u0645|\u0641\u064a\u0644\u0645\u0633|\u0641\u064a\u0627\u0644|\u0627\u0645\u0628\u0648\u0644|\u0645\u0628\u0648\u0644|\u0623\u0645\u0628\u0648\u0644|\u0644\u0628\u0648\u0633|\u062a\u062d\u0627\u0645\u064a\u0644|\u062a\u062d\u0645\u064a\u0644\u0629)",
    re.IGNORECASE,
)
_PACK_AFTER_FORM_RE = re.compile(
    r"\b(?:tab|tabs|tablet|tablets|cap|caps|capsule|capsules|film|films|flim|flims|vial|vials|amp|amps|ampoule|ampoules|supp|suppository|suppositories|lozenge|lozenges|gummy|gummies)\s*(\d+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CanonicalStrength:
    value: float
    unit: str


@dataclass(frozen=True)
class CanonicalConcentration:
    """A compound strength with an ordered numerator/denominator relationship."""

    numerator: tuple[CanonicalStrength, ...]
    denominator: tuple[CanonicalStrength, ...]


@dataclass(frozen=True)
class ProductAttributes:
    forms: frozenset[str]
    strengths: frozenset[CanonicalStrength]
    packs: frozenset[int]
    concentrations: frozenset[CanonicalConcentration] = field(default_factory=frozenset)


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
    strengths.update(
        CanonicalStrength(float(match.group(1)), "drops-dose")
        for match in _BARE_DROPS_DOSE_RE.finditer(normalized)
    )
    concentrations = {
        concentration
        for match in _COMPOUND_RE.finditer(normalized)
        if (concentration := _canonical_concentration(match.group("expression")))
    }
    for concentration in concentrations:
        strengths.update(concentration.numerator)
        strengths.update(concentration.denominator)
    packs = {
        int(match.group(1) or match.group(2))
        for match in _PACK_RE.finditer(normalized)
    }
    packs.update(int(match.group(1)) for match in _PACK_AFTER_FORM_RE.finditer(normalized))
    return ProductAttributes(
        frozenset(forms),
        frozenset(strengths),
        frozenset(packs),
        frozenset(concentrations),
    )


def _normalize_attribute_text(text: str) -> str:
    """Normalize documented supplier typos without changing brand tokens."""
    normalized = (text or "").casefold().translate(
        str.maketrans(
            "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫",
            "01234567890123456789.",
        )
    )
    normalized = normalized.replace("ـ", "").replace("\\", "/")
    # Supplier workbooks commonly write international units as ``i.u`` or
    # ``i.u.``. Treat the dotted abbreviation as the same explicit IU unit so
    # a missing strength cannot be mistaken for a compatible vial.
    normalized = re.sub(r"\bi\s*[.]\s*u[.]?\b", "iu", normalized)
    # Supplier exports use both ``30 F.C. TABS`` and ``30 F.C.TABS``.
    # Remove only the dotted abbreviation so the existing pack parser sees
    # the explicit count while ordinary product tokens remain unchanged.
    normalized = re.sub(r"\bf\s*[.]\s*c[.]?\s*", "", normalized)
    normalized = re.sub(r"[\u064B-\u065F\u0670]", "", normalized)
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
        pattern = rf"(?<![a-z0-9])(?:\d+\s*)?{re.escape(alias)}(?![a-z])"
        return bool(re.search(pattern, text, re.IGNORECASE))
    return alias in text


def _canonical_strength(match: re.Match[str]) -> CanonicalStrength:
    value = float(match.group(1) or match.group(3))
    raw_unit = (match.group(2) or match.group(4) or "").casefold()
    return _canonical_strength_from_parts(value, raw_unit)


def _canonical_strength_from_parts(value: float, raw_unit: str) -> CanonicalStrength:
    unit = {
        "mcg": "mcg", "µg": "mcg", "ug": "mcg", "\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645": "mcg",
        "mg": "mg", "\u0645\u062c\u0645": "mg", "\u0645\u0644\u062c\u0645": "mg",
        "g": "mg", "gm": "mg", "\u062c\u0631\u0627\u0645": "mg", "\u062c\u0645": "mg",
        "ml": "ml", "\u0645\u0644": "ml", "iu": "iu", "\u0648\u062d\u062f\u0629": "iu", "%": "%",
    }[raw_unit]
    if raw_unit in {"g", "gm", "\u062c\u0631\u0627\u0645", "\u062c\u0645"}:
        value *= 1000
    return CanonicalStrength(value, unit)


def _canonical_concentration(expression: str) -> CanonicalConcentration | None:
    """Parse a slash expression without losing compound or ratio semantics."""
    parts: list[tuple[float, str | None]] = []
    for raw_part in expression.split("/"):
        match = _COMPOUND_PART_RE.fullmatch(raw_part.strip())
        if not match:
            return None
        parts.append(
            (
                float(match.group("number")),
                match.group("unit").casefold() if match.group("unit") else None,
            )
        )
    if len(parts) < 2:
        return None

    explicit_units = {
        _canonical_strength_from_parts(1.0, raw_unit).unit
        for _, raw_unit in parts
        if raw_unit is not None
    }
    if not explicit_units:
        return None

    all_parts_have_units = all(raw_unit is not None for _, raw_unit in parts)
    if len(explicit_units) == 1 and not (len(parts) == 2 and all_parts_have_units):
        common_unit = next(iter(explicit_units))
        canonical_parts = tuple(
            _canonical_strength_from_parts(value, raw_unit or common_unit)
            for value, raw_unit in parts
        )
        return CanonicalConcentration(
            numerator=tuple(sorted(canonical_parts, key=_strength_sort_key)),
            denominator=(),
        )

    canonical_parts = tuple(
        _canonical_strength_from_parts(
            value,
            raw_unit or next(iter(explicit_units)),
        )
        for value, raw_unit in parts
    )
    return CanonicalConcentration(
        numerator=(canonical_parts[0],),
        denominator=canonical_parts[1:],
    )


def _strength_sort_key(strength: CanonicalStrength) -> tuple[str, float]:
    return strength.unit, strength.value


def _mismatch_reason(query: ProductAttributes, candidate: ProductAttributes) -> str:
    if query.forms and not candidate.forms:
        return "candidate form is not proven"
    if query.forms and not (query.forms & candidate.forms):
        return "candidate form conflicts with requested form"
    if query.concentrations:
        if not candidate.concentrations:
            return "candidate concentration is not proven"
        if not all(
            concentration in candidate.concentrations
            for concentration in query.concentrations
        ):
            return "candidate concentration conflicts with requested concentration"
    if query.strengths and not candidate.strengths:
        return "candidate strength is not proven"
    if query.strengths and not all(
        _strength_is_proven(
            required,
            candidate.strengths,
            query.forms,
            candidate.forms,
        )
        for required in query.strengths
    ):
        return "candidate strength conflicts with requested strength"
    if not query.strengths and candidate.strengths:
        return "candidate has an unrequested strength"
    if query.packs and not candidate.packs:
        return "candidate pack is not proven"
    if query.packs and not (query.packs & candidate.packs):
        return "candidate pack conflicts with requested pack"
    return ""


def _strength_is_proven(
    required: CanonicalStrength,
    candidate_strengths: frozenset[CanonicalStrength],
    query_forms: frozenset[str],
    candidate_forms: frozenset[str],
) -> bool:
    """Allow an unqualified drops dose to match an explicit mg drops strength."""
    if required in candidate_strengths:
        return True
    if required.unit != "drops-dose":
        return False
    if "DROPS" not in query_forms or "DROPS" not in candidate_forms:
        return False
    return any(
        strength.unit == "mg" and strength.value == required.value
        for strength in candidate_strengths
    )


__all__ = [
    "CanonicalConcentration",
    "CanonicalStrength",
    "CompatibilityResult",
    "ProductAttributes",
    "extract_product_attributes",
    "validate_product_compatibility",
]
