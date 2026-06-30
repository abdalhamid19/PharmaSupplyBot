"""Category-aware search query template helpers."""

from __future__ import annotations

from ..core.drug_matching.normalization.normalizer import parse_drug


def category_queries(name: str) -> list[str]:
    """Generate category-aware queries based on the drug's form and fields."""
    parsed = parse_drug(name)
    if not parsed.brand:
        return []

    brand = parsed.brand
    volume = parsed.volume
    form = parsed.form
    dosage = _get_dosage_string(parsed)

    if form in {"SYRUP", "SUSP", "SOLUTION"} or bool(volume):
        return _liquid_queries(brand, volume, dosage)

    if form in {"AMP", "VIAL"}:
        return _injection_queries(brand, dosage, form)

    return []


def _get_dosage_string(parsed) -> str:
    """Return a joined dosage string from drug components."""
    if not parsed.dosage_nums or not parsed.dosage_units:
        return ""
    parts = [f"{n}{u}" for n, u in zip(parsed.dosage_nums, parsed.dosage_units)]
    return " ".join(parts)


def _liquid_queries(brand: str, volume: str, dosage: str) -> list[str]:
    """Generate queries for liquid form products."""
    queries = []
    if volume:
        queries.append(f"{brand} {volume}")
    if dosage:
        queries.append(f"{brand} {dosage}")
    return queries


def _injection_queries(brand: str, dosage: str, form: str) -> list[str]:
    """Generate queries for injection form products."""
    queries = []
    if dosage and form:
        queries.append(f"{brand} {dosage} {form}")
    if dosage:
        queries.append(f"{brand} {dosage}")
    return queries
