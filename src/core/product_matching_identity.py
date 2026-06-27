"""Identity validation and variant rejection logic for product matching."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .product_matching_helpers import (
    _ARABIC_NON_WORD_RE,
    _ARABIC_REQUIRED_TOKEN_ALIASES,
    _ARABIC_WHITESPACE_RE,
    _GENERIC_IDENTITY_TOKENS,
)


def _candidate_variant_rejection(query: str, candidate: dict[str, Any]) -> str:
    from .product_matching_scoring import _normalized_tokens

    query_tokens = set(_normalized_tokens(query))
    reasons = _synthetic_name_rejection_reasons(query_tokens, candidate)
    reasons.extend(_missing_english_identity_reasons(query_tokens, candidate))
    arabic_name = _normalized_arabic_name(candidate)
    if arabic_name:
        reasons.extend(_missing_arabic_token_reasons(query_tokens, arabic_name))
        if _vitacid_c_calcium_conflict(query_tokens, arabic_name):
            reasons.append("Arabic name contains calcium for VITACID C query")
    return "; ".join(reasons)


def _normalized_arabic_name(candidate: dict[str, Any]) -> str:
    raw_name = str(candidate.get("productName") or "").strip()
    spaced_name = _ARABIC_NON_WORD_RE.sub(" ", raw_name)
    return _ARABIC_WHITESPACE_RE.sub(" ", spaced_name).strip()


def _synthetic_name_rejection_reasons(
    query_tokens: set[str], candidate: dict[str, Any]
) -> list[str]:
    if not candidate.get("productNameEnSynthetic"):
        return []
    if _missing_english_identity_reasons(query_tokens, candidate):
        return ["Synthetic English name missing requested identity token"]
    return []


def _missing_english_identity_reasons(
    query_tokens: set[str], candidate: dict[str, Any]
) -> list[str]:
    from .product_matching_scoring import _candidate_english_name, _normalized_tokens

    candidate_tokens = set(_normalized_tokens(_candidate_english_name(candidate)))
    identity_tokens = _identity_tokens(query_tokens)
    if identity_tokens and not _any_identity_match(identity_tokens, candidate_tokens):
        return ["English name missing requested identity token"]
    return []


def _any_identity_match(identity_tokens: set[str], candidate_tokens: set[str]) -> bool:
    if identity_tokens & candidate_tokens:
        return True
    return any(
        _fuzzy_token_match(qt, ct)
        for qt in identity_tokens
        if len(qt) >= 4
        for ct in candidate_tokens
        if len(ct) >= 4
    )


def _fuzzy_token_match(a: str, b: str) -> bool:
    return (
        a.startswith(b)
        or b.startswith(a)
        or SequenceMatcher(None, a, b).ratio() >= 0.85
    )


def _identity_tokens(tokens: set[str]) -> set[str]:
    return {
        token
        for token in tokens
        if len(token) > 1
        and not token.isdigit()
        and token not in _GENERIC_IDENTITY_TOKENS
    }


def _missing_arabic_token_reasons(tokens: set[str], arabic_name: str) -> list[str]:
    reasons: list[str] = []
    for token, aliases in _ARABIC_REQUIRED_TOKEN_ALIASES.items():
        if token in tokens and not any(alias in arabic_name for alias in aliases):
            reasons.append(f"Arabic name missing marker for {token}")
    return reasons


def _vitacid_c_calcium_conflict(tokens: set[str], arabic_name: str) -> bool:
    return "VITACID" in tokens and "C" in tokens and "كالسيوم" in arabic_name
