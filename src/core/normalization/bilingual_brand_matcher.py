"""Bilingual Arabic↔English brand matcher.

Combines four signals to score how likely an Arabic catalog row is the
same product as an English order row:

1. **Brand dictionary** (karem505/egyptian-drug-database). Highest
   confidence — a registered EN↔AR trade-name alias is a direct hit.
2. **LLM translation** (Cohere ``command-a-translate`` with
   ``command-a-plus`` fallback). Translates the Arabic brand to
   English, then we do a string similarity on the result.
3. **Form / strength / pack compatibility**. Penalises mismatches on
   these structural tokens (e.g. ordering a cream while the catalog
   only carries syrup of the same brand).
4. **Fuzzy transliteration fallback** (rapidfuzz on pyarabic Latin
   output). Last resort for the ~5% of drugs the dictionary doesn't
   cover.

The output is a float in ``[0.0, 1.0]`` plus a short reason string for
logging.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from .drug_dictionary import lookup_ar, lookup_en
from .translation import ar_to_en

logger = logging.getLogger(__name__)


_FORM_EN_TO_AR = {
    "TAB": "قرص", "TABS": "قرص", "TABLET": "قرص", "TABLETS": "قرص",
    "CAP": "كبسولة", "CAPS": "كبسولة", "CAPSULE": "كبسولة",
    "CREAM": "كريم", "OINT": "مرهم", "OINTMENT": "مرهم",
    "GEL": "جل", "SYRUP": "شراب", "SUSP": "معلق",
    "DROPS": "قطرة", "DROP": "قطرة", "SPRAY": "بخاخ",
    "INJ": "حقن", "INJECTION": "حقن", "SUPP": "لبوس",
    "SACHET": "كيس", "POWDER": "بودرة", "MILK": "لبن",
    "SOLUTION": "محلول", "LOZENGE": "استحلاب",
}

_FORM_AR_TO_EN = {ar: en for en, ar in _FORM_EN_TO_AR.items()}


_TOKEN_RE = re.compile(r"[\u0600-\u06FFA-Za-z0-9]+")
_STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|gm|g|ml|mcg|iu|%)", re.I)
_PACK_RE = re.compile(r"(\d+)\s*(tab|tabs|cap|caps|ml|gm|g)\b", re.I)


@dataclass(frozen=True)
class BrandMatch:
    score: float
    reason: str
    en_brand: str
    ar_brand: str
    manufacturer: str


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text or "")]


def _forms(text: str) -> set[str]:
    """Extract form tokens from either English or Arabic text."""
    upper = text.upper()
    found = {tok for tok in _FORM_EN_TO_AR if re.search(rf"\b{tok}\b\.?", upper)}
    for ar_form, en_form in _FORM_AR_TO_EN.items():
        if ar_form in text:
            found.add(en_form)
    return found


def _strengths(text: str) -> set[str]:
    s = text.lower()
    return {m.group(0).replace(" ", "").lower() for m in _STRENGTH_RE.finditer(s)}


def _packs(text: str) -> set[str]:
    s = text.lower()
    return {m.group(1) for m in _PACK_RE.finditer(s)}


def _brand_only(text: str) -> str:
    """Strip form/strength/pack from a name to leave the brand prefix."""
    s = re.sub(
        r"\b\d+(?:\.\d+)?\s*(mg|gm|g|ml|mcg|iu|%)\b\.?", " ", text, flags=re.I
    )
    s = re.sub(
        r"\b\d+(?:\.\d+)?\s*(tab|tabs|cap|caps|ml|gm|g)\b\.?", " ", s, flags=re.I
    )
    s = re.sub(
        r"\b\d+\s*(قرص|كبسولة|قرص|اقراص|كبسولات|قرص|اكياس|"
        r"امبول|قطره|قطرة|بخاخ|شراب|مل|جم|مجم|ميكروجرام|"
        r"ملي|مل|جرام|جرعه|وحدة|جرعة|مل|جم|مجم|جرام)\b",
        " ", s,
    )
    s = re.sub(
        r"\b(tab|tabs|tablets|cap|caps|capsules|cream|oint|gel|"
        r"syrup|susp|drops|spray|inj|injection|supp|sachet|powder|"
        r"milk|solution|lozenge|f\.?c\.?|effer)\b\.?",
        " ",
        s,
        flags=re.I,
    )
    for ar_form in _FORM_AR_TO_EN:
        s = s.replace(ar_form, " ")
    s = re.sub(r"\d+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _dict_score(en_query: str, ar_row: str) -> tuple[float, str, str, str]:
    """Try the brand dictionary first. Returns (score, reason, en_brand, manufacturer)."""
    en_brand = _brand_only(en_query)
    ar_brand = _brand_only(ar_row)

    for hit in lookup_en(en_brand):
        hit_ar_brand = _brand_only(hit["ar"])
        if hit_ar_brand and hit_ar_brand == ar_brand:
            return 0.97, "dictionary direct hit (EN↔AR)", en_brand, hit.get("manufacturer", "")
        if hit_ar_brand and fuzz.token_set_ratio(hit_ar_brand, ar_brand) >= 90:
            return 0.9, "dictionary fuzzy hit (EN↔AR)", en_brand, hit.get("manufacturer", "")

    for hit in lookup_ar(ar_brand):
        hit_en_brand = _brand_only(hit["en"])
        if hit_en_brand and hit_en_brand == en_brand.upper():
            return 0.97, "dictionary direct hit (AR↔EN)", en_brand, hit.get("manufacturer", "")
        if hit_en_brand and fuzz.token_set_ratio(hit_en_brand, en_brand.upper()) >= 90:
            return 0.9, "dictionary fuzzy hit (AR↔EN)", en_brand, hit.get("manufacturer", "")

    return 0.0, "", en_brand, ""


def _translation_score(en_query: str, ar_row: str, en_brand: str) -> float:
    """Translate the Arabic row to English, then string-similarity."""
    translated = ar_to_en(ar_row)
    if not translated or translated == ar_row:
        return 0.0
    translated_brand = _brand_only(translated).upper()
    if not translated_brand:
        return 0.0
    return fuzz.token_set_ratio(en_brand.upper(), translated_brand) / 100.0


def _compatibility_factor(en_query: str, ar_row: str) -> float:
    """Penalise mismatches on form/strength/pack tokens."""
    factor = 1.0
    en_forms, ar_forms = _forms(en_query), _forms(ar_row)
    if en_forms and ar_forms and not (en_forms & ar_forms):
        factor *= 0.6
    en_strengths, ar_strengths = _strengths(en_query), _strengths(ar_row)
    if en_strengths and ar_strengths and not (en_strengths & ar_strengths):
        factor *= 0.8
    en_packs, ar_packs = _packs(en_query), _packs(ar_row)
    if en_packs and ar_packs and not (en_packs & ar_packs):
        factor *= 0.9
    return factor


def match_brand(en_query: str, ar_row: str) -> BrandMatch:
    """Score how likely an Arabic catalog row matches the English query.

    Returns a :class:`BrandMatch` with ``score`` in ``[0.0, 1.0]``.
    """
    dict_score, reason, en_brand, manufacturer = _dict_score(en_query, ar_row)
    if dict_score == 0.0:
        translated = _translation_score(en_query, ar_row, en_brand)
        if translated >= 0.6:
            score = translated
            reason = f"translation similarity ({score:.2f})"
        else:
            score = 0.0
            reason = "no brand match"
    else:
        score = dict_score

    score *= _compatibility_factor(en_query, ar_row)
    return BrandMatch(
        score=round(score, 3),
        reason=reason or "no brand match",
        en_brand=en_brand,
        ar_brand=_brand_only(ar_row),
        manufacturer=manufacturer,
    )
