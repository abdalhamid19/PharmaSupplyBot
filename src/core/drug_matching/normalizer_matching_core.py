"""Core component matching logic orchestrator."""

from .normalizer_parsing import DrugComponents
from .normalizer_constants import (
    BABY_FORMULA_MODIFIERS, CRITICAL_MODIFIERS, VITAMIN_MODIFIERS
)
from .normalizer_matching_helpers import (
    _has_reliable_english_name,
    _modifier_is_optional,
    _insulin_variant_signature,
    _variant_tokens,
    _has_pediatric_signal,
    _has_adult_signal,
)
from .normalizer_matching_brand import _brand_match_check
from .normalizer_matching_dosage import _dosage_match_check
from .normalizer_matching_form import _other_match_check


def components_match(d: DrugComponents, m: DrugComponents, brand_prefix_min: int = 4) -> tuple[bool, str]:
    """Verify two drug components represent the same product. Returns (is_match, reason)."""
    
    # Critical modifier check (must come before brand check for safety)
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        # Check for unsafe modifiers first (PLUS, EXTRA, FORTE, etc.)
        critical_modifiers = {
            "PLUS",
            "EXTRA",
            "FORTE",
            "MAX",
            "SUPER",
            "ADVANCE",
        }
        d_critical = d_words & critical_modifiers
        m_critical = m_words & critical_modifiers
        if d_critical != m_critical:
            return False, "different_modifier"

        # Check for age group differences (ADULT vs KIDS, etc.)
        age_keywords = {
            "ADULT",
            "ADULTS",
            "KID",
            "KIDS",
            "CHILDREN",
            "BABY",
            "INFANT",
            "INFANTS",
            "PEDIATRIC",
            "PAEDIATRIC",
        }
        d_age = d_words & age_keywords
        m_age = m_words & age_keywords
        if d_age != m_age:
            return False, "different_age_group"

        # Check for flavor differences (MINT vs GREEN, etc.)
        flavor_keywords = {
            "MINT",
            "GREEN",
            "CHOCOLATE",
            "VANILLA",
            "STRAWBERRY",
            "ORANGE",
            "LEMON",
            "BERRY",
        }
        d_flavor = d_words & flavor_keywords
        m_flavor = m_words & flavor_keywords
        if d_flavor != m_flavor:
            return False, "different_flavor"
    
    # Brand check
    brand_ok, brand_reason = _brand_match_check(d, m, brand_prefix_min)
    if not brand_ok:
        return False, brand_reason
    
    # Import status check
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        if d.imported != m.imported:
            return False, "different_import_status"
    
    # Check for INF vs dosage mismatch (INF usually means no specific dosage)
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        d_has_inf = 'INF' in d_words
        m_has_inf = 'INF' in m_words
        d_has_dosage = bool(d.dosage_nums)
        m_has_dosage = bool(m.dosage_nums)
        
        # If one has INF and the other has dosage, reject
        if d_has_inf != m_has_inf:
            if d_has_dosage or m_has_dosage:
                return False, "different_dosage"
    
    # Additional modifier check (non-critical modifiers)
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        modifiers_to_check = (CRITICAL_MODIFIERS | VITAMIN_MODIFIERS) - {
            "PLUS",
            "EXTRA",
            "FORTE",
            "MAX",
            "SUPER",
            "ADVANCE",
        }
        if d.product_class == "baby_food" or m.product_class == "baby_food":
            modifiers_to_check |= BABY_FORMULA_MODIFIERS
        
        for modifier in modifiers_to_check:
            if (modifier in d_words) != (modifier in m_words):
                if _modifier_is_optional(modifier, d_words, m_words):
                    continue
                return False, "different_modifier"
        d_insulin = _insulin_variant_signature(d)
        m_insulin = _insulin_variant_signature(m)
        if (d_insulin or m_insulin) and d_insulin != m_insulin:
            return False, "different_modifier"
        d_variants = _variant_tokens(d)
        m_variants = _variant_tokens(m)
        if d_variants and m_variants and d_variants.isdisjoint(m_variants):
            return False, "different_flavor"
    
    # Product class check
    if d.product_class != m.product_class and d.product_class != "medicine" and m.product_class != "medicine":
        return False, "different_product_class"
    
    # Dosage check
    dosage_ok, dosage_reason = _dosage_match_check(d, m)
    if not dosage_ok:
        return False, dosage_reason
    
    # Form, quantity, volume, weight, flavor check
    other_ok, other_reason = _other_match_check(d, m)
    if not other_ok:
        return False, other_reason
    
    return True, "ok"


__all__ = [
    "components_match",
]
