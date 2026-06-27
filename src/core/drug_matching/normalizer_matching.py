"""Drug component matching and compatibility logic."""

import re
from rapidfuzz import fuzz
from .normalizer_parsing import DrugComponents
from .normalizer_constants import (
    ADULT_WORDS, BABY_FORMULA_MODIFIERS, CONNECTOR_WORDS, CRITICAL_CHEMICALS,
    CRITICAL_MODIFIERS, FLAVOR_WORDS, INFUSION_CONTEXT_WORDS, LIQUID_DOSE_FORMS,
    OCULAR_FORMS, LIQUID_FORMS, PEDIATRIC_WORDS, ROUTE_WORDS, SOFT_BRAND_DESCRIPTORS,
    SOLID_FORMS, VITAMIN_MODIFIERS, COLOR_WORDS
)


def components_match(d: DrugComponents, m: DrugComponents, brand_prefix_min: int = 4) -> tuple[bool, str]:
    """Verify two drug components represent the same product. Returns (is_match, reason)."""
    d_clean = re.sub(r"[^A-Z0-9]", "", d.brand)
    m_clean = re.sub(r"[^A-Z0-9]", "", m.brand)
    
    d_words_upper = set(w.upper() for w in d.normalized.split()) | set(w.upper() for w in d.brand.split())
    m_words_upper = set(w.upper() for w in m.normalized.split()) | set(w.upper() for w in m.brand.split())
    d_chems = d_words_upper & CRITICAL_CHEMICALS
    m_chems = m_words_upper & CRITICAL_CHEMICALS
    if d_chems and m_chems and d_chems != m_chems:
        return False, "different_brand"
    
    if _has_reliable_english_name(d) and _has_reliable_english_name(m):
        if d.imported != m.imported:
            return False, "different_import_status"
    
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    
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
    
    if d_clean and m_clean:
        brand_exception = _known_brand_variant_match(d, m, d_clean, m_clean)
        shorter = min(len(d_clean), len(m_clean))
        prefix_len = min(len(d_clean), len(m_clean), max(brand_prefix_min, int(shorter * 0.75)))
        prefix_len = min(prefix_len, len(d_clean), len(m_clean))
        if prefix_len > 0 and d_clean[:prefix_len] != m_clean[:prefix_len]:
            if d_clean not in m_clean and m_clean not in d_clean and fuzz.ratio(d_clean, m_clean) < 86 and not brand_exception:
                return False, "different_brand"
        if d_clean != m_clean and d_clean not in m_clean and m_clean not in d_clean:
            if fuzz.ratio(d_clean, m_clean) < 86 and not brand_exception:
                return False, "different_brand"
        if d_clean != m_clean and (d_clean in m_clean or m_clean in d_clean):
            shorter = min(len(d_clean), len(m_clean))
            longer = max(len(d_clean), len(m_clean))
            if longer - shorter > 2 and fuzz.ratio(d_clean, m_clean) < 86 and not brand_exception:
                return False, "different_brand"
    
    if d.product_class != m.product_class and d.product_class != "medicine" and m.product_class != "medicine":
        return False, "different_product_class"
    
    dosage_checked_compatible = False
    if d.dosage_nums and m.dosage_nums:
        if not _dosage_compatible(d, m):
            return False, "different_dosage"
        dosage_checked_compatible = True
    if not dosage_checked_compatible:
        if _has_reliable_english_name(d) and _has_reliable_english_name(m):
            d_numeric = _component_numeric_signals(d)
            m_numeric = _component_numeric_signals(m)
            d_matched_dosage = False
            m_matched_dosage = False
            if d_numeric and m.dosage_nums:
                if _numeric_signals_match_dosage(d_numeric, m.dosage_nums):
                    d_matched_dosage = True
                else:
                    return False, "different_dosage"
            if m_numeric and d.dosage_nums:
                if _numeric_signals_match_dosage(m_numeric, d.dosage_nums):
                    m_matched_dosage = True
                else:
                    return False, "different_dosage"
            if d.product_class == "baby_food" or m.product_class == "baby_food":
                if _has_stage_mismatch(d_numeric, m_numeric):
                    return False, "different_baby_formula_stage"
            if d_numeric and m_numeric and d_numeric != m_numeric and not d_matched_dosage and not m_matched_dosage:
                return False, "different_dosage"
    
    if d.form and m.form and not _forms_compatible(d.form, m.form):
        return False, "different_form"
    
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


def _modifier_is_optional(modifier, d_words, m_words):
    if modifier == "ADVANCE" and "MILK" in d_words and "MILK" in m_words:
        return True
    if modifier == "EXTRA" and ("EMOLLIENT" in d_words or "EMOLLIENT" in m_words):
        return True
    if modifier == "NASAL" and ({"SPRAY", "SPRAYS", "DOSES"} & d_words) and ({"SPRAY", "SPRAYS", "DOSES"} & m_words):
        return True
    if modifier == "NASAL" and ({"DROPS", "DROP", "EYE"} & d_words) and ({"DROPS", "DROP", "EYE"} & m_words):
        return True
    if modifier == "VAGINAL" and ({"SUPP", "SUPPS", "CAP", "CAPS", "CAPSULE", "CAPSULES"} & d_words) and ({"SUPP", "SUPPS", "CAP", "CAPS", "CAPSULE", "CAPSULES"} & m_words):
        return True
    if modifier == "R" and "PROLONGED" in (d_words | m_words):
        return True
    if modifier == "SR" and "RETARD" in (d_words | m_words):
        return True
    if modifier == "MOUTH" and ("MOUTHWASH" in d_words or "MOUTHWASH" in m_words) and ("WASH" in d_words or "WASH" in m_words):
        return True
    return False


def _insulin_variant_signature(c):
    if "INSULINAGYPT" not in c.normalized.replace(" ", ""):
        return frozenset()
    words = set(c.normalized.split())
    variants = set(words & {"N", "R"})
    if re.search(r"\b70\s*/\s*30\b", c.normalized):
        variants.add("70/30")
    return frozenset(variants)


def _variant_tokens(c):
    words = set(c.normalized.split())
    return frozenset(words & (FLAVOR_WORDS | COLOR_WORDS))


def _has_pediatric_signal(words):
    if words & PEDIATRIC_WORDS:
        return True
    if "INF" not in words:
        return False
    return not bool(words & INFUSION_CONTEXT_WORDS)


def _has_adult_signal(words):
    return bool(words & ADULT_WORDS)


def _route_signals(words):
    routes = set(words & ROUTE_WORDS)
    if {"I", "M"} <= words:
        routes.add("IM")
    if {"I", "V"} <= words:
        routes.add("IV")
    if {"S", "C"} <= words:
        routes.add("SC")
    return frozenset(routes)


def _forms_compatible(left, right):
    if not left or not right or left == right:
        return True
    if left in OCULAR_FORMS and right in OCULAR_FORMS:
        return True
    if left in LIQUID_FORMS and right in LIQUID_FORMS:
        return True
    if left in SOLID_FORMS and right in SOLID_FORMS:
        return True
    return False


def _known_brand_variant_match(d, m, d_clean, m_clean):
    d_words = set(d.normalized.split())
    m_words = set(m.normalized.split())
    if {d_clean, m_clean} == {"EPOETIN", "EPOETINSEDICO"}:
        return True
    if d.product_class == m.product_class == "baby_food":
        if "BEBELAC" in d_words and "BEBELAC" in m_words:
            return ("BEBEJUNIOR" in d_words) == ("BEBEJUNIOR" in m_words)
    if "CONCOR" in d_words and "CONCOR" in m_words:
        return "PLUS" in d_words and "PLUS" in m_words
    return False


def _dosage_compatible(d, m):
    canonical = _matching_canonical_dosage(d, m)
    if canonical is not None:
        return canonical
    d_parts = _dosage_parts(d.dosage_nums)
    m_parts = _dosage_parts(m.dosage_nums)
    if _concor_plus_dosage_compatible(d_parts, m_parts, d, m):
        return True
    if tuple(sorted(d_parts, key=float)) == tuple(sorted(m_parts, key=float)):
        return True
    if _summed_combo_matches_single(d_parts, m_parts):
        return True
    if _liquid_total_matches_per_5(d_parts, m_parts, d, m):
        return True
    return _liquid_primary_strength_matches(d_parts, m_parts, d, m)


def _liquid_primary_strength_matches(d_parts, m_parts, d, m):
    if not ({d.form, m.form} & LIQUID_DOSE_FORMS):
        return False
    return (len(d_parts) == 1 and len(m_parts) > 1 and d_parts[0] == m_parts[0]) or (len(m_parts) == 1 and len(d_parts) > 1 and m_parts[0] == d_parts[0])


def _matching_canonical_dosage(d, m):
    left = _canonical_dosage_values_mg(d)
    right = _canonical_dosage_values_mg(m)
    if not left or not right:
        return None
    return tuple(sorted(left)) == tuple(sorted(right))


def _canonical_dosage_values_mg(c):
    if len(c.dosage_nums) != len(c.dosage_units):
        return ()
    values = []
    for num, unit in zip(c.dosage_nums, c.dosage_units):
        value = _canonical_dosage_value_mg(num, unit)
        if value is None:
            return ()
        values.append(value)
    return tuple(values)


def _canonical_dosage_value_mg(num, unit):
    if "/" in num:
        return None
    value = float(num)
    normalized_unit = unit.replace(" ", "").upper()
    if normalized_unit in {"GM", "G"}:
        return value * 1000.0
    if normalized_unit == "MG":
        return value
    if normalized_unit == "MCG":
        return value / 1000.0
    return None


def _concor_plus_dosage_compatible(left, right, d, m):
    words = set(d.normalized.split()) | set(m.normalized.split())
    if not {"CONCOR", "PLUS"} <= words:
        return False
    if not left or not right:
        return False
    return left[0] == right[0]


def _liquid_total_matches_per_5(left, right, d, m):
    forms = {d.form, m.form}
    if not forms & LIQUID_DOSE_FORMS:
        return False
    try:
        if len(left) == 1 and len(right) == 2:
            return _single_per_5_matches_total(left[0], right[0], right[1], m.volume)
        if len(right) == 1 and len(left) == 2:
            return _single_per_5_matches_total(right[0], left[0], left[1], d.volume)
    except ValueError:
        return False
    return False


def _single_per_5_matches_total(single, total, total_volume, parsed_volume):
    if parsed_volume and _canonical_number(parsed_volume) != _canonical_number(total_volume):
        return False
    return abs((float(total) / float(total_volume)) - (float(single) / 5.0)) <= 0.01


def _summed_combo_matches_single(left, right):
    if len(left) <= 1 and len(right) <= 1:
        return False
    try:
        left_vals = [float(v) for v in left]
        right_vals = [float(v) for v in right]
    except ValueError:
        return False
    if len(left_vals) > 1 and len(right_vals) == 1:
        return abs(sum(left_vals) - right_vals[0]) <= 0.01
    if len(right_vals) > 1 and len(left_vals) == 1:
        return abs(sum(right_vals) - left_vals[0]) <= 0.01
    return False


def _dosage_parts(nums):
    parts = []
    for num in nums:
        parts.extend(p for p in num.split("/") if p)
    return parts


def _canonical_number(value):
    return str(float(value)).rstrip("0").rstrip(".") if "." in value else value


def _component_numeric_signals(c):
    signals = list(_unmatched_numeric_signals(c))
    words = set(c.normalized.split())
    if c.product_class == "baby_food" and "BEBEJUNIOR" in words and "+" in words:
        try:
            signals.remove("1")
        except ValueError:
            pass
    return tuple(signals)


def _unmatched_numeric_signals(c):
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


def _dosage_flat_set(dosage_nums):
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


def _numeric_signals_match_dosage(signals, dosage_nums):
    return all(s in _dosage_flat_set(dosage_nums) for s in signals)


def _qty_is_misclassified_dosage(a, b):
    if not a.qty or not b.dosage_nums:
        return False
    return a.qty in _dosage_flat_set(b.dosage_nums)


def _has_reliable_english_name(c):
    if c.is_synthetic:
        return False
    text = c.normalized or ""
    return any(char.isalpha() and char.isascii() for char in text)


def _has_stage_mismatch(d_numeric, m_numeric):
    d_stages = {s for s in d_numeric if s in {"1", "2", "3", "4", "5"}}
    m_stages = {s for s in m_numeric if s in {"1", "2", "3", "4", "5"}}
    if d_stages and m_stages and d_stages != m_stages:
        return True
    if (d_stages and not m_stages) or (m_stages and not d_stages):
        return True
    return False
