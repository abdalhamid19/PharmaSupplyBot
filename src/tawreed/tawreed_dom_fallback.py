"""Synthetic English names for Tawreed DOM-only product rows."""

from __future__ import annotations

import re

_NUMERIC_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?")
_OCR_ZERO_RE = re.compile(r"(?<=\d)[Oo](?=\b|[^A-Za-z0-9])")
_WHITESPACE_RE = re.compile(r"\s+")


def fallback_english_name(query: str, arabic_name: str) -> str:
    """Return a synthetic English name using query words and DOM row numbers."""
    normalized_query = normalize_fallback_query(query)
    q_tokens = [t for t in _WHITESPACE_RE.split(normalized_query) if t]
    query_numbers = _NUMERIC_TOKEN_RE.findall(normalized_query)
    row_numbers = _NUMERIC_TOKEN_RE.findall(arabic_name)
    if query_numbers and set(query_numbers).issubset(set(row_numbers)):
        return normalized_query
    non_num = [t for t in q_tokens if not any(ch.isdigit() for ch in t)]
    return " ".join(non_num + row_numbers) or normalized_query


def normalize_fallback_query(query: str) -> str:
    """Normalize OCR zeros and compact numeric tokens for DOM plausibility checks."""
    text = _OCR_ZERO_RE.sub("0", query.strip())
    text = re.sub(r"([A-Za-z])(?=\d)", r"\1 ", text)
    text = re.sub(r"(?<=\d)([A-Za-z])", r" \1", text)
    return _WHITESPACE_RE.sub(" ", text).strip()
