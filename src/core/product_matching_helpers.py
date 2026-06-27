"""Product matching constants and basic helper functions."""

import re
from typing import Any

_OCR_ZERO_RE = re.compile(r"(?<=\d)[Oo](?=\b|[^A-Za-z0-9])")
_TOKEN_BOUNDARY_RE = re.compile(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")
_ARABIC_NON_WORD_RE = re.compile(r"[^\w\u0600-\u06FF]+")
_ARABIC_WHITESPACE_RE = re.compile(r"\s+")
_NUMERIC_PART_RE = re.compile(r"\d+")

MAX_SEARCH_QUERY_VARIANTS = 24

_ARABIC_REQUIRED_TOKEN_ALIASES = {
    "APPLE": ("تفاح", "ابل"),
    "AR": ("ايه ار", "اي ار", "ارتجاع"),
    "DOUCHE": ("دش", "غسول", "مهبل"),
    "EFF": ("فوار",),
    "LOTION": ("لوشن", "لوسيون"),
    "ML": ("مل", "مللي", "ميللي"),
    "VAG": ("مهبل", "المهبل", "نسائي"),
    "VAGINAL": ("مهبل", "المهبل", "نسائي"),
}

_GENERIC_IDENTITY_TOKENS = {
    "ANTISEPTIC", "AMP", "AMPS", "CAP", "CAPS", "COUGH", "BAG", "BAGS",
    "CAPSULE", "CAPSULES", "CREAM", "DROP", "DROPS", "EFF", "EYE", "FILTER",
    "FLAVOR", "FLAVOUR", "G", "GEL", "GM", "IMP", "INJ", "INJECTION", "LOTION",
    "MCG", "MG", "MILK", "ML", "O", "OINTMENT", "ORAL", "POWDER", "SHAMPOO",
    "SOAP", "SOLN", "SOLUTION", "SPRAY", "SYRUP", "TAB", "TABS", "TABLET",
    "TABLETS", "VIAL"
}


def normalize_text(value: str) -> str:
    """Normalize product text so Arabic and English matching stay stable."""
    text = _OCR_ZERO_RE.sub("0", str(value or "")).upper()
    text = re.sub(r"(\d)\.(\d{3})(?=\D|$)", r"\1\2", text)
    text = _TOKEN_BOUNDARY_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalized_tokens(value: str) -> list[str]:
    """Return normalized tokens for a search term or candidate name."""
    return normalize_text(value).split()


def unique_non_empty(values: list[str]) -> list[str]:
    """Remove empty values and duplicates while preserving query order."""
    out, seen = [], set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def candidate_texts(candidate: dict[str, Any]) -> set[str]:
    """Return all normalized text representations of a candidate."""
    texts = set()
    for key in ("productName", "productNameEn"):
        value = candidate.get(key)
        if value:
            texts.add(normalize_text(value))
    return texts


def candidate_english_name(candidate: dict[str, Any]) -> str:
    """Return the English name of a candidate."""
    return str(candidate.get("productNameEn") or candidate.get("productName") or "")


def numeric_tokens(text: str) -> set[str]:
    """Extract all numeric tokens from text."""
    return set(_NUMERIC_PART_RE.findall(text))


def numeric_match_count(query: str, candidate: str) -> int:
    """Count how many query numeric tokens appear in candidate."""
    query_nums = numeric_tokens(query)
    candidate_nums = numeric_tokens(candidate)
    return len(query_nums & candidate_nums)


def normalized_arabic_name(name: str) -> str:
    """Normalize an Arabic product name for matching."""
    if not name or not isinstance(name, str):
        return ""
    text = name.strip()
    text = _ARABIC_NON_WORD_RE.sub(" ", text)
    return _ARABIC_WHITESPACE_RE.sub(" ", text).strip()


def identity_tokens(text: str) -> set[str]:
    """Extract identity tokens (non-generic) from normalized text."""
    tokens = set(normalize_text(text).split())
    return tokens - _GENERIC_IDENTITY_TOKENS


def fuzzy_token_match(token_a: str, token_b: str, threshold: float = 0.85) -> bool:
    """Check if two tokens are similar enough via fuzzy matching."""
    from difflib import SequenceMatcher
    if token_a == token_b:
        return True
    ratio = SequenceMatcher(None, token_a, token_b).ratio()
    return ratio >= threshold


def any_identity_match(req_tokens: set[str], cand_tokens: set[str]) -> bool:
    """Check if any identity token matches between request and candidate."""
    if req_tokens & cand_tokens:
        return True
    for rt in req_tokens:
        for ct in cand_tokens:
            if fuzzy_token_match(rt, ct):
                return True
    return False


def vitacid_c_calcium_conflict(query: str, candidate: dict[str, Any]) -> bool:
    """Detect VITACID-C vs VITACID CALCIUM confusion."""
    query_norm = normalize_text(query)
    cand_texts = candidate_texts(candidate)
    if "VITACIDC" in query_norm or "VITACID C" in query_norm:
        return any("CALCIUM" in t for t in cand_texts)
    if "VITACIDCALCIUM" in query_norm or "VITACID CALCIUM" in query_norm:
        return any("VITACIDC" in t and "CALCIUM" not in t for t in cand_texts)
    return False
