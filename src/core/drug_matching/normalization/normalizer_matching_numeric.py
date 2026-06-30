"""Numeric signal extraction and matching helpers."""

import re
from .normalizer_parsing import DrugComponents


def _canonical_number(value) -> str:
    """Canonicalize number representation."""
    return str(float(value)).rstrip("0").rstrip(".") if "." in value else value


def _component_numeric_signals(c: DrugComponents) -> tuple:
    """Extract numeric signals not consumed by dosage/qty/volume/weight."""
    signals = list(_unmatched_numeric_signals(c))
    words = set(c.normalized.split())
    if c.product_class == "baby_food" and "BEBEJUNIOR" in words and "+" in words:
        try:
            signals.remove("1")
        except ValueError:
            pass
    return tuple(signals)


def _unmatched_numeric_signals(c: DrugComponents) -> tuple:
    """Find numeric signals not matched to dosage/qty/volume/weight."""
    nums = re.findall(r"\b\d+(?:\.\d+)?\b", c.normalized)
    consumed = list(_dosage_parts(c.dosage_nums))
    consumed.extend(v for v in (c.qty, c.volume, c.weight) if v)
    out = []
    for num in nums:
        normalized = str(float(num)).rstrip("0").rstrip(".") if "." in num else num
        consumed_idx = next((i for i, v in enumerate(consumed) if v == num or v == normalized), None)
        if consumed_idx is not None:
            consumed.pop(consumed_idx)
        else:
            out.append(normalized)
    return tuple(out)


def _dosage_parts(nums) -> list:
    """Split dosage numbers by '/'."""
    parts = []
    for num in nums:
        parts.extend(p for p in num.split("/") if p)
    return parts


def _dosage_flat_set(dosage_nums) -> set:
    """Create flat set of dosage numbers."""
    flat = set()
    for num in dosage_nums:
        for part in num.split("/"):
            s = part.strip()
            if not s:
                continue
            flat.add(s)
            if "." in s:
                flat.add(str(float(s)).rstrip("0").rstrip("."))
    return flat


def _numeric_signals_match_dosage(signals, dosage_nums) -> bool:
    """Check if numeric signals match dosage numbers."""
    return all(s in _dosage_flat_set(dosage_nums) for s in signals)


def _qty_is_misclassified_dosage(a: DrugComponents, b: DrugComponents) -> bool:
    """Check if qty is actually a misclassified dosage."""
    if not a.qty or not b.dosage_nums:
        return False
    return a.qty in _dosage_flat_set(b.dosage_nums)


def _has_stage_mismatch(d_numeric, m_numeric) -> bool:
    """Check if baby formula stages mismatch."""
    d_stages = {s for s in d_numeric if s in {"1", "2", "3", "4", "5"}}
    m_stages = {s for s in m_numeric if s in {"1", "2", "3", "4", "5"}}
    if d_stages and m_stages and d_stages != m_stages:
        return True
    if (d_stages and not m_stages) or (m_stages and not d_stages):
        return True
    return False


__all__ = [
    "_canonical_number",
    "_component_numeric_signals",
    "_unmatched_numeric_signals",
    "_dosage_parts",
    "_dosage_flat_set",
    "_numeric_signals_match_dosage",
    "_qty_is_misclassified_dosage",
    "_has_stage_mismatch",
]
