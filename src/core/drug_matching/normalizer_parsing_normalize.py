"""Normalization functions for drug names."""

from __future__ import annotations

import re
from .normalizer_parsing_constants import _NOISE_PREFIX_RE, _AR_DIACRITICS_RE


def normalize_arabic(name: str) -> str:
    """Normalize Arabic product text for auxiliary matching signals."""
    if not name or not isinstance(name, str):
        return ""
    text = _AR_DIACRITICS_RE.sub("", name.strip())
    text = re.sub("[إأآٱ]", "ا", text)
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(name: str) -> str:
    """Normalize an English drug/product name before parsing or fuzzy matching."""
    if not name or not isinstance(name, str):
        return ""
    name = name.strip().upper()
    name = _NOISE_PREFIX_RE.sub("", name)
    name = name.replace("_", " ").replace("\\", " / ")
    name = re.sub(r"-+", " ", name)
    name = re.sub(r"[()]", " ", name)
    name = re.sub(r"(?<=\d)O(?=\d)", "0", name)
    name = re.sub(r"\bFORET\b", "FORTE", name)
    name = re.sub(r"\b(SYRP|SYP)\b", "SYRUP", name)
    name = re.sub(r"\bVAG\b", "VAGINAL", name)
    name = name.replace("*", " / ")
    name = re.sub(r"(?<=\d)O(?=\s*ML\b)", "0", name)
    name = re.sub(r"(?<=%)([A-Z])", r" \1", name)
    name = re.sub(r"([A-Z])(?=\d)", r"\1 ", name)
    name = re.sub(r"(?<=\d)([A-Z])", r" \1", name)
    name = re.sub(r"\b(\d+)\s*M\b(?!\s*\.)", r"\1 MG", name)
    name = re.sub(r"\b(\d+)\s*M\s*/", r"\1 MG /", name)
    name = re.sub(r"\bANDOFLOZIN XR 25 MG\s*/\s*100 MG\b", "ANDOFLOZIN XR 25 / 1000 MG", name)
    name = re.sub(r"\b([BD])\s+(3|6|12)\b", r"\1\2", name)
    name = re.sub(r"\s*[\\/]\s*", " / ", name)
    name = re.sub(r"(\d)\.(\d{3})\s*(I\.?U\.?|IU|MCG|MG)", r"\1\2 \3", name)
    name = re.sub(r"(?<!\d)\.(\d+)", r"0.\1", name)
    name = re.sub(r"\.(?!\d)", " ", name)
    name = re.sub(r"(?<!\d)\.", " ", name)
    name = re.sub(r"\b([DESCMX])\s+R\b", r"\1R", name)
    name = re.sub(r"\bUNITS?\b", "IU", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _convert_arabic_to_english_terms(name: str) -> str:
    """Convert Arabic numerals and unit/form keywords to English equivalents."""
    text = name.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return _apply_term_replacements(text)


def _apply_term_replacements(text: str) -> str:
    replacements = {
        r"\b(?:مجم|ملجم|مليجرام|مليجرم)\b": " MG ", r"\b(?:مل|ملل|مللي|ميللي|مللتر)\b": " ML ",
        r"\b(?:جم|جرام|جرم)\b": " GM ", r"\b(?:قرص|اقراص|قراص)\b": " TAB ",
        r"\b(?:كبسول|كبسولات|كبسوله)\b": " CAP ", r"\b(?:امبول|امبولات)\b": " AMP ",
        r"\b(?:فيال|فيلات|فيالات)\b": " VIAL ", r"\b(?:نقط|قطره|قطرات)\b": " DROPS ",
        r"\b(?:بخاخ|بخاخة|سبراي)\b": " SPRAY ", r"\b(?:لبن|حليب)\b": " MILK ",
        r"\b(?:شراب|شرب)\b": " SYRUP ", r"\b(?:كريم|دهان)\b": " CREAM ",
        r"\b(?:جل|جيل)\b": " GEL ", r"\b(?:مرهم)\b": " OINTMENT ",
        r"\b(?:ايه\s+ار|اي\s+ار|ارتجاع)\b": " AR ",
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text
