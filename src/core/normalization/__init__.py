"""Public API for the drug-name normalization utilities."""
from .bilingual_brand_matcher import BrandMatch, match_brand
from .drug_dictionary import load_dictionary, lookup_ar, lookup_en
from .translation import ar_to_en

__all__ = [
    "BrandMatch",
    "ar_to_en",
    "load_dictionary",
    "lookup_ar",
    "lookup_en",
    "match_brand",
]
