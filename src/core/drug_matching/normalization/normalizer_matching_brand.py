"""Brand matching logic for drug components."""

import re
from rapidfuzz import fuzz
from .normalizer_parsing import DrugComponents
from .normalizer_constants import CRITICAL_CHEMICALS


def _brand_match_check(d: DrugComponents, m: DrugComponents, brand_prefix_min: int) -> tuple[bool, str]:
    """Check if brands match between two components."""
    # First check manufacturer compatibility
    if d.manufacturer and m.manufacturer:
        # Both have manufacturers - they must match
        if d.manufacturer != m.manufacturer:
            from ...identity.manufacturer_identity import manufacturer_conflict
            if manufacturer_conflict(d.manufacturer, m.manufacturer, threshold=0.85):
                return False, f"different_manufacturer: {d.manufacturer} vs {m.manufacturer}"
    
    # Now check brand (without manufacturer)
    d_clean = re.sub(r"[^A-Z0-9]", "", d.brand)
    m_clean = re.sub(r"[^A-Z0-9]", "", m.brand)
    
    d_words_upper = set(w.upper() for w in d.normalized.split()) | set(
        w.upper() for w in d.brand.split()
    )
    m_words_upper = set(w.upper() for w in m.normalized.split()) | set(
        w.upper() for w in m.brand.split()
    )
    d_chems = d_words_upper & CRITICAL_CHEMICALS
    m_chems = m_words_upper & CRITICAL_CHEMICALS
    if d_chems and m_chems and d_chems != m_chems:
        return False, "different_brand"
    
    if d_clean and m_clean:
        brand_exception = _known_brand_variant_match(d, m, d_clean, m_clean)
        if _co_prefixed_brand_mismatch(d_clean, m_clean) and not brand_exception:
            return False, "different_brand"
        shorter = min(len(d_clean), len(m_clean))
        prefix_len = min(len(d_clean), len(m_clean), max(brand_prefix_min, int(shorter * 0.75)))
        prefix_len = min(prefix_len, len(d_clean), len(m_clean))
        if prefix_len > 0 and d_clean[:prefix_len] != m_clean[:prefix_len]:
            if (
                d_clean not in m_clean
                and m_clean not in d_clean
                and fuzz.ratio(d_clean, m_clean) < 86
                and not brand_exception
            ):
                return False, "different_brand"
        if d_clean != m_clean and d_clean not in m_clean and m_clean not in d_clean:
            if fuzz.ratio(d_clean, m_clean) < 86 and not brand_exception:
                return False, "different_brand"
        if d_clean != m_clean and (d_clean in m_clean or m_clean in d_clean):
            shorter = min(len(d_clean), len(m_clean))
            longer = max(len(d_clean), len(m_clean))
            if (
                longer - shorter > 2
                and fuzz.ratio(d_clean, m_clean) < 86
                and not brand_exception
            ):
                return False, "different_brand"
            # COAVAZIR vs AVAZIR has ratio ~85.7 with len_diff 2; treat as distinct.
            if longer - shorter == 2 and fuzz.ratio(d_clean, m_clean) < 86:
                return False, "different_brand"
    
    return True, "ok"


def _co_prefixed_brand_mismatch(left_clean: str, right_clean: str) -> bool:
    """Return True when one brand is exactly CO + the other (distinct product line)."""
    if not left_clean or not right_clean or left_clean == right_clean:
        return False
    longer, shorter = (
        (left_clean, right_clean)
        if len(left_clean) >= len(right_clean)
        else (right_clean, left_clean)
    )
    return longer == f"CO{shorter}"


def _known_brand_variant_match(d: DrugComponents, m: DrugComponents, d_clean: str, m_clean: str) -> bool:
    """Check for known brand variant matches."""
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    if {d_clean, m_clean} == {"EPOETIN", "EPOETINSEDICO"}:
        return True
    if d.product_class == m.product_class == "baby_food":
        if "BEBELAC" in d_words and "BEBELAC" in m_words:
            return ("BEBEJUNIOR" in d_words) == ("BEBEJUNIOR" in m_words)
    if {"ISIS", "CINNAMON", "GINGER"} <= d_words | m_words:
        return {"ISIS", "CINNAMON"} <= d_words and {"ISIS", "CINNAMON"} <= m_words
    if "CONCOR" in d_words and "CONCOR" in m_words:
        return "PLUS" in d_words and "PLUS" in m_words
    return False


__all__ = [
    "_brand_match_check",
    "_co_prefixed_brand_mismatch",
    "_known_brand_variant_match",
]
