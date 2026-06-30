"""Form, quantity, volume, weight, and flavor matching logic."""

from .normalizer_parsing import DrugComponents
from .normalizer_constants import OCULAR_FORMS, LIQUID_FORMS, SOLID_FORMS
from .normalizer_matching_helpers import _has_reliable_english_name
from .normalizer_matching_numeric import _qty_is_misclassified_dosage


def _other_match_check(d: DrugComponents, m: DrugComponents) -> tuple[bool, str]:
    """Check form, quantity, volume, weight, and flavor matching."""
    if d.form and m.form and not _forms_compatible(d.form, m.form):
        return False, "different_form"
    
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        d_routes = _route_signals(d_words)
        m_routes = _route_signals(m_words)
        if d_routes and m_routes and d_routes.isdisjoint(m_routes):
            return False, "different_route"
    
    if d.qty and m.qty and d.qty != m.qty:
        if d.form == "POWDER" and m.form == "POWDER":
            return True, "ok"
        if _qty_is_misclassified_dosage(d, m) or _qty_is_misclassified_dosage(m, d):
            pass
        else:
            return False, "different_quantity"
    
    if d.volume and m.volume and d.volume != m.volume:
        if d.form == "SYRUP" and m.form == "SYRUP":
            return True, "ok"
        return False, "different_volume"
    
    if d.weight and m.weight and d.weight != m.weight:
        return False, "different_weight"
    
    if d.flavor and m.flavor and d.flavor != m.flavor:
        return False, "different_flavor"
    
    return True, "ok"


def _forms_compatible(left: str, right: str) -> bool:
    """Check if two forms are compatible."""
    if not left or not right or left == right:
        return True
    if left in OCULAR_FORMS and right in OCULAR_FORMS:
        return True
    if left in LIQUID_FORMS and right in LIQUID_FORMS:
        return True
    if left in SOLID_FORMS and right in SOLID_FORMS:
        return True
    return False


def _route_signals(words) -> frozenset:
    """Extract route signals from words."""
    from .normalizer_constants import ROUTE_WORDS
    routes = set(words & ROUTE_WORDS)
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return frozenset(routes)


__all__ = [
    "_other_match_check",
    "_forms_compatible",
    "_route_signals",
]
