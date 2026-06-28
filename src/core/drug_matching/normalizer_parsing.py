"""Drug name parsing and normalization functions."""

from __future__ import annotations

from .normalizer_parsing_constants import (
    _DOSAGE_RE, _MG_PER_ML_RE, _COMBO_MG_PER_ML_RE, _WEIGHT_RE,
    _QTY_RE, _VOL_RE, _NOISE_PREFIX_RE, _IMPORT_MARKER_RE, _AR_DIACRITICS_RE,
    ACRONYM_BRANDS, BRAND_QUALIFIERS, FLAVOR_WORDS, FORM_PREFIXES,
    FORM_SCAN_ORDER, FORM_WORDS, INFUSION_CONTEXT_WORDS, LIQUID_DOSE_FORMS,
    NOISE_WORDS, PEDIATRIC_WORDS, SOFT_BRAND_DESCRIPTORS, SUPPLEMENT_WORDS,
    BABY_FOOD_WORDS, COSMETIC_WORDS, DEVICE_WORDS, CONNECTOR_WORDS,
)
from .normalizer_parsing_normalize import (
    normalize_arabic,
    normalize,
    _convert_arabic_to_english_terms,
    _apply_term_replacements,
)
from .normalizer_parsing_parse import (
    DrugComponents,
    parse_drug,
    _canonical_form,
)
from .normalizer_parsing_inference import (
    _infer_missing_dosage,
    _is_brand_boundary,
    _canonical_number,
    _weight_is_strength,
    _is_pediatric_inf,
    _is_descriptive_brand_word,
)
from .normalizer_parsing_classification import (
    classify_product,
    brand_variants_from_words,
)

__all__ = [
    "DrugComponents",
    "normalize_arabic",
    "normalize",
    "parse_drug",
    "classify_product",
    "brand_variants_from_words",
    "_DOSAGE_RE",
    "_MG_PER_ML_RE",
    "_COMBO_MG_PER_ML_RE",
    "_WEIGHT_RE",
    "_QTY_RE",
    "_VOL_RE",
    "_NOISE_PREFIX_RE",
    "_IMPORT_MARKER_RE",
    "_AR_DIACRITICS_RE",
    "ACRONYM_BRANDS",
    "BRAND_QUALIFIERS",
    "FLAVOR_WORDS",
    "FORM_PREFIXES",
    "FORM_SCAN_ORDER",
    "FORM_WORDS",
    "INFUSION_CONTEXT_WORDS",
    "LIQUID_DOSE_FORMS",
    "NOISE_WORDS",
    "PEDIATRIC_WORDS",
    "SOFT_BRAND_DESCRIPTORS",
    "SUPPLEMENT_WORDS",
    "BABY_FOOD_WORDS",
    "COSMETIC_WORDS",
    "DEVICE_WORDS",
    "CONNECTOR_WORDS",
    "_convert_arabic_to_english_terms",
    "_apply_term_replacements",
    "_canonical_form",
    "_infer_missing_dosage",
    "_is_brand_boundary",
    "_canonical_number",
    "_weight_is_strength",
    "_is_pediatric_inf",
    "_is_descriptive_brand_word",
]
