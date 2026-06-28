"""Product classification and brand variant functions."""

from __future__ import annotations

import re
from .normalizer_parsing_constants import (
    FORM_PREFIXES, FORM_WORDS, NOISE_WORDS, BRAND_QUALIFIERS,
    SOFT_BRAND_DESCRIPTORS, CONNECTOR_WORDS,
    BABY_FOOD_WORDS, COSMETIC_WORDS, DEVICE_WORDS, SUPPLEMENT_WORDS,
    INFUSION_CONTEXT_WORDS,
)
from .normalizer_parsing_inference import _is_pediatric_inf


def classify_product(norm):
    words = set(norm.split())
    if {"PRE", "FILLED"} <= words and "SYRINGE" in words:
        return "medicine"
    if words & DEVICE_WORDS:
        return "device"
    if words & BABY_FOOD_WORDS and not words & {"BODY", "CREAM", "LOTION"}:
        return "baby_food"
    if words & COSMETIC_WORDS:
        return "cosmetic"
    if words & SUPPLEMENT_WORDS:
        return "supplement"
    return "medicine"


def brand_variants_from_words(words, primary_brand):
    variants = []
    def add(value):
        cleaned = re.sub(r"[^A-Z0-9]", "", value)
        if len(cleaned) >= 3 and cleaned not in variants:
            variants.append(cleaned)
    add(primary_brand)
    prefix = []
    for idx, word in enumerate(words):
        if re.search(r"\d", word):
            break
        if word in FORM_PREFIXES or word in FORM_WORDS or word in NOISE_WORDS:
            break
        if _is_pediatric_inf(words, idx):
            break
        if idx > 0 and word in CONNECTOR_WORDS:
            continue
        if idx > 0 and word in BRAND_QUALIFIERS:
            break
        prefix.append(word)
        add("".join(prefix))
        if idx > 0 and word in SOFT_BRAND_DESCRIPTORS:
            break
    return tuple(variants)
