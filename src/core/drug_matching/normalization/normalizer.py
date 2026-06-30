"""Name normalization and drug component parsing - Facade module."""

# Re-export all public APIs from split modules
from .normalizer_constants import *  # noqa: F401, F403
from .normalizer_parsing import (  # noqa: F401
    DrugComponents,
    normalize,
    normalize_arabic,
    parse_drug,
    classify_product,
    brand_variants_from_words,
)
from .normalizer_matching import components_match  # noqa: F401

__all__ = [
    "DrugComponents",
    "normalize",
    "normalize_arabic",
    "parse_drug",
    "classify_product",
    "brand_variants_from_words",
    "components_match",
]
