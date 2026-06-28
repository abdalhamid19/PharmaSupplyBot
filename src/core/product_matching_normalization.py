"""Text normalization utilities for product matching."""

import re

from .product_matching_helpers import (
    _NON_ALNUM_RE,
    _OCR_ZERO_RE,
    _TOKEN_BOUNDARY_RE,
    _WHITESPACE_RE,
)


def _normalize_text(value: str) -> str:
    """Normalize product text so Arabic and English matching stay stable."""
    text = _OCR_ZERO_RE.sub("0", str(value or "")).upper()
    text = re.sub(r"(\d)\.(\d{3})(?=\D|$)", r"\1\2", text)
    text = _TOKEN_BOUNDARY_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalized_tokens(value: str) -> list[str]:
    """Return normalized tokens for a search term or candidate name."""
    return _normalize_text(value).split()
