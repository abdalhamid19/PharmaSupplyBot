"""Numeric token validation logic for product matching."""

from __future__ import annotations

import re
from typing import Any

from .drug_matching.normalization.normalizer import components_match, parse_drug
from .product_matching_safe_omission import _any_safe_omission


def _numeric_safe_acceptance(
    query: str,
    candidate: dict[str, Any],
    acceptance: tuple[bool, str, str],
) -> tuple[bool, str, str]:
    """Reject fuzzy matches that add unrequested numeric product details."""
    from .product_matching_scoring import _candidate_english_name

    cand_name = _candidate_english_name(candidate)
    extra = _unrequested_numeric_tokens(query, cand_name)
    extra = _ignore_component_safe_numeric_tokens(extra, query, cand_name)
    if acceptance[0] and acceptance[1] != "exact_normalized_name_match" and extra:
        tokens = ", ".join(sorted(extra))
        return False, "", f"Candidate has unrequested numeric token: {tokens}"
    return acceptance


def _unrequested_numeric_tokens(query: str, candidate_name: str) -> set[str]:
    from .product_matching_scoring import _numeric_tokens, _normalize_text

    query_tokens = _numeric_tokens(_normalize_text(query))
    candidate_tokens = _numeric_tokens(_normalize_text(candidate_name))
    extra_tokens = candidate_tokens - query_tokens
    extra_tokens = _ignore_liquid_per_5_marker(extra_tokens, query, candidate_name)
    extra_tokens = _ignore_unit_dose_pack_markers(extra_tokens, query, candidate_name)
    if not query_tokens and len(extra_tokens) <= 1:
        return set()
    if len(extra_tokens) == 1 and _single_percentage_token(
        extra_tokens, candidate_name
    ):
        return set()
    return extra_tokens


def _ignore_component_safe_numeric_tokens(
    tokens: set[str], query: str, candidate_name: str
) -> set[str]:
    if not tokens:
        return tokens
    requested = parse_drug(query)
    offered = parse_drug(candidate_name)
    compatible, _reason = components_match(requested, offered)
    if not compatible:
        return tokens
    if _any_safe_omission(tokens, requested, offered):
        return set()
    return tokens


def _ignore_liquid_per_5_marker(
    tokens: set[str], query: str, candidate_name: str
) -> set[str]:
    from .product_matching_scoring import _normalize_text

    if "5" not in tokens or "ML" not in _normalize_text(query):
        return tokens
    if re.search(r"\b5\s*ML\b", str(candidate_name).upper()):
        return {token for token in tokens if token != "5"}
    return tokens


def _ignore_unit_dose_pack_markers(
    tokens: set[str], query: str, candidate_name: str
) -> set[str]:
    if not tokens or not _unit_dose_context(query, candidate_name):
        return tokens
    from .product_matching_scoring import _normalize_text

    candidate_text = _normalize_text(candidate_name)
    return {
        token for token in tokens if not _is_unit_dose_pack_token(token, candidate_text)
    }


def _unit_dose_context(query: str, candidate_name: str) -> bool:
    from .product_matching_scoring import _normalize_text

    candidate_words = set(_normalize_text(candidate_name).split())
    if not {"UNIT", "DOSE"} <= candidate_words:
        return False
    requested = parse_drug(query)
    offered = parse_drug(candidate_name)
    if not ({requested.form, offered.form} & {"VIAL", "AMP", "SPRAY"}):
        return False
    compatible, reason = components_match(requested, offered)
    return compatible or reason != "different_dosage"


def _is_unit_dose_pack_token(token: str, candidate_text: str) -> bool:
    escaped = re.escape(token)
    return bool(re.search(rf"\b{escaped}\s*(ML|UNIT|DOSE)\b", candidate_text))


def _single_percentage_token(tokens: set[str], candidate_name: str) -> bool:
    token = next(iter(tokens))
    return f"{token}%" in str(candidate_name)
