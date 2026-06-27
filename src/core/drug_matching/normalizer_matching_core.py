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
    # Brand check
    brand_ok, brand_reason = _brand_match_check(d, m, brand_prefix_min)
    if not brand_ok:
        return False, brand_reason
    
    # Import status check
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        if d.imported != m.imported:
            return False, "different_import_status"
    
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    
    # Modifier check
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        modifiers_to_check = CRITICAL_MODIFIERS | VITAMIN_MODIFIERS
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
        d_pediatric = _has_pediatric_signal(d_words)
        m_pediatric = _has_pediatric_signal(m_words)
        if d_pediatric != m_pediatric:
            return False, "different_age_group"
        if (_has_adult_signal(d_words) and m_pediatric) or (_has_adult_signal(m_words) and d_pediatric):
            return False, "different_age_group"
    
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
