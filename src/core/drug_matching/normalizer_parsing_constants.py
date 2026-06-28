"""Regex patterns and constants for drug name parsing."""

from __future__ import annotations

import re
from .normalizer_constants import (
    ACRONYM_BRANDS, BRAND_QUALIFIERS, FLAVOR_WORDS, FORM_PREFIXES,
    FORM_SCAN_ORDER, FORM_WORDS, INFUSION_CONTEXT_WORDS, LIQUID_DOSE_FORMS,
    NOISE_WORDS, PEDIATRIC_WORDS, SOFT_BRAND_DESCRIPTORS, SUPPLEMENT_WORDS,
    BABY_FOOD_WORDS, COSMETIC_WORDS, DEVICE_WORDS, CONNECTOR_WORDS,
)

_DOSAGE_RE = re.compile(
    r"(\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?(?:\s\d{3})?)\s*(MG|MCG|I\s*U|IU|%)(?=$|\s)",
    re.IGNORECASE
)
_MG_PER_ML_RE = re.compile(r"(\d+(?:\.\d+)?)\s*MG\s*/\s*(\d+(?:\.\d+)?)\s*ML", re.IGNORECASE)
_COMBO_MG_PER_ML_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*MG\s*/\s*(\d+(?:\.\d+)?)\s*ML",
    re.IGNORECASE
)
_WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(GM|G)\b", re.IGNORECASE)
_QTY_RE = re.compile(
    r"(\d+)\s*(?:(?:F\s*C|FC|SCORED|CHEWABLE|EFF|EFFERVESCENT|VAGINAL|VAG|PRE\s*FILLED|PREFILLED|METERED)\s*)?"
    r"(TABLETS|TABLET|TABS|TAB|CAPSULES|CAPSULE|CAPS|CAP|SACHETS|SACHET|SACH|AMPOULES|AMPOULE|AMPS|AMP|VIAL|"
    r"SUPPS|SUPP|PIECE|DROPS|PENS|PEN|CARTRIDGES|CARTIRIDGES|CARTRIDGE|SYRINGES|SYRINGE|GUMMIES|GUM|PACKETS|"
    r"DOSES|METERED)\b",
    re.IGNORECASE
)
_VOL_RE = re.compile(r"(\d+(?:\.\d+)?)\s*ML\b", re.IGNORECASE)
_NOISE_PREFIX_RE = re.compile(r"^[+*.]+\s*(IMP|IMPORTED)?\s*", re.IGNORECASE)
_IMPORT_MARKER_RE = re.compile(r"(^[+*.]+\s*(IMP|IMPORTED))|\b(IMP|IMPORTED)\b", re.IGNORECASE)
_AR_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670]")

__all__ = [
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
]
