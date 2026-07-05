"""Acceptance logic and identity validation for product matching — consolidated."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .candidate_identity import candidate_has_store_product_id, candidate_store_product_id
from ..drug_matching.normalization.normalizer import components_match, parse_drug
from .matching_penalties import compatibility_rejection_reason
from .product_matching_helpers import (
    _ARABIC_NON_WORD_RE,
    _ARABIC_REQUIRED_TOKEN_ALIASES,
    _ARABIC_WHITESPACE_RE,
    _GENERIC_IDENTITY_TOKENS,
    _NUMERIC_PART_RE,
    _NON_ALNUM_RE,
    _OCR_ZERO_RE,
    _TOKEN_BOUNDARY_RE,
    _WHITESPACE_RE,
    _normalize_text,
    _normalized_tokens,
)
from ..config.config_models import MatchingConfig
from ..identity.manufacturer_identity import (
    extract_manufacturer_from_candidate,
    extract_manufacturer_from_name,
    manufacturer_conflict,
)
from .product_matching_scoring import (
    _candidate_english_name,
)


# ── Normalization utilities (from product_matching_normalization.py) ──


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


# ── Component matching (from product_matching_components.py) ──


def _candidate_component_rejection(query: str, candidate: dict[str, Any]) -> str:
    """Return a rejection reason when parsed drug components are incompatible."""
    candidate_name = _candidate_english_name(candidate)
    if not candidate_name:
        return ""
    requested = parse_drug(query)
    offered = parse_drug(candidate_name)
    offered.is_synthetic = bool(candidate.get("productNameEnSynthetic"))
    if not requested.brand or not offered.brand:
        return ""
    is_match, reason = components_match(requested, offered)
    if is_match:
        return ""
    return f"Semantic token conflict: {reason}"


# ── Identity validation (from product_matching_identity.py) ──


def _candidate_variant_rejection(query: str, candidate: dict[str, Any]) -> str:
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


# ── Orderable acceptance (from product_matching_orderable.py) ──


def _orderable_acceptance(
    candidate: dict[str, Any], acceptance: tuple[bool, str, str]
) -> tuple[bool, str, str]:
    """Reject otherwise-accepted candidates that cannot be used for ordering."""
    if acceptance[0] and not candidate_has_store_product_id(candidate):
        return False, "", "Candidate missing orderable storeProductId"
    return acceptance


# ── Safe omission logic (from product_matching_safe_omission.py) ──


def _any_safe_omission(tokens: set[str], requested, offered) -> bool:
    """True when the extra numeric tokens represent a safe pharmaceutical omission."""
    return (
        _safe_omitted_combo_strength(requested, offered)
        or _safe_omitted_topical_strength(requested, offered)
        or _safe_omitted_solid_pack_size(tokens, requested, offered)
        or _safe_omitted_injection_volume(tokens, requested, offered)
        or _safe_omitted_effervescent_strength(requested, offered)
        or _safe_omitted_liquid_concentration(tokens, requested, offered)
        or _safe_omitted_pack_count(tokens, requested, offered)
        or _safe_omitted_pen_insulin_details(tokens, requested, offered)
        or _safe_omitted_baby_food_pack_size(tokens, requested, offered)
        or _safe_omitted_percentage_concentration(tokens, requested, offered)
    )


def _safe_omitted_combo_strength(requested, offered) -> bool:
    words = set(requested.normalized.split()) | set(offered.normalized.split())
    return bool(
        {"CONCOR", "PLUS"} <= words and requested.dosage_nums and offered.dosage_nums
    )


def _safe_omitted_topical_strength(requested, offered) -> bool:
    if requested.dosage_nums or not offered.dosage_nums:
        return False
    if requested.volume and offered.volume and requested.volume != offered.volume:
        return False
    if requested.product_class == offered.product_class == "cosmetic":
        return True
    topical_forms = {"CREAM", "GEL", "LOTION", "OINT", "SOLUTION", "SPRAY"}
    return bool({requested.form, offered.form} & topical_forms)


def _safe_omitted_solid_pack_size(tokens: set[str], requested, offered) -> bool:
    if not requested.dosage_nums or not offered.qty or requested.qty:
        return False
    if offered.qty not in tokens or offered.form not in {"TAB", "CAP"}:
        return False
    return {requested.form, offered.form} <= {"", "TAB", "CAP"}


def _safe_omitted_injection_volume(tokens: set[str], requested, offered) -> bool:
    if not requested.dosage_nums or not offered.dosage_nums:
        return False
    if not offered.volume or offered.volume not in tokens:
        return False
    if requested.volume or requested.form not in {"AMP", "VIAL"}:
        return False
    return offered.form in {"AMP", "VIAL"}


def _safe_omitted_effervescent_strength(requested, offered) -> bool:
    if requested.dosage_nums or not offered.dosage_nums:
        return False
    words = set(requested.normalized.split()) | set(offered.normalized.split())
    if not {"VITACID", "C"} <= words or not (words & {"EFF", "EFFERVESCENT"}):
        return False
    if requested.qty and offered.qty and requested.qty != offered.qty:
        return False
    return {requested.form, offered.form} <= {"", "TAB"}


def _safe_omitted_liquid_concentration(tokens: set[str], requested, offered) -> bool:
    if not _dosage_or_shared_strength(requested, offered):
        return False
    cand_upper = str(offered.normalized).upper()
    volume_parts: set[str] = set()
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(?:MG|MCG|IU)\s*/\s*(\d+(?:\.\d+)?)\s*ML",
        cand_upper,
    ):
        volume_parts.add(m.group(2))
    if offered.volume:
        volume_parts.add(offered.volume)
    if not volume_parts:
        return False
    return tokens <= volume_parts


def _safe_omitted_pack_count(tokens: set[str], requested, offered) -> bool:
    if not _dosage_or_shared_strength(requested, offered):
        return False
    if not offered.qty:
        return False
    pack_tokens = {offered.qty}
    return tokens <= pack_tokens


def _dosage_or_shared_strength(requested, offered) -> bool:
    if requested.dosage_nums and offered.dosage_nums:
        return bool(set(requested.dosage_nums) & set(offered.dosage_nums))
    if not offered.dosage_nums:
        return False
    query_nums = _numeric_tokens(requested.normalized)
    if query_nums & set(offered.dosage_nums):
        return True
    req_text = requested.normalized
    return any(d in req_text for d in offered.dosage_nums)


def _safe_omitted_pen_insulin_details(tokens: set[str], requested, offered) -> bool:
    pen_forms = {"PEN", "CARTRIDGE"}
    if not ({requested.form, offered.form} & pen_forms):
        return False
    if requested.dosage_nums and offered.dosage_nums:
        if set(requested.dosage_nums) != set(offered.dosage_nums):
            return False
    return True


def _safe_omitted_baby_food_pack_size(tokens: set[str], requested, offered) -> bool:
    """Allow pack size omission for baby food products like milk powder."""
    if requested.product_class != "baby_food":
        return False
    if not offered.qty:
        offered_nums = _numeric_tokens(offered.normalized)
        if offered_nums and offered_nums & tokens:
            return True
    if offered.qty and offered.qty in tokens:
        return True
    return False


def _numeric_tokens(text: str) -> set[str]:
    """Return tokens that contain at least one digit."""
    return {
        numeric_part
        for token in text.split()
        for numeric_part in _NUMERIC_PART_RE.findall(token)
    }


def _safe_omitted_percentage_concentration(tokens: set[str], requested, offered) -> bool:
    """Allow percentage concentration omission for topical/eye drop products."""
    if not offered.dosage_nums:
        return False
    topical_forms = {"CREAM", "GEL", "LOTION", "SOLUTION", "SPRAY", "DROPS", "OINTMENT", "EYE"}
    if not ({requested.form, offered.form} & topical_forms):
        return False
    if "%" in offered.dosage_units:
        return True
    return False


# ── Manufacturer mismatch check ──


def _candidate_manufacturer_rejection(
    query: str,
    candidate: dict[str, Any],
    config: dict[str, Any] | MatchingConfig,
) -> tuple[bool, str | None]:
    """Check for manufacturer conflict between query and candidate."""
    enable_check = (
        config.enable_manufacturer_check
        if hasattr(config, "enable_manufacturer_check")
        else config.get("enable_manufacturer_check", False)
    )
    if not enable_check:
        return True, None

    query_company = extract_manufacturer_from_name(query)
    candidate_name = _candidate_english_name(candidate)
    candidate_company = extract_manufacturer_from_candidate(
        candidate_name,
        candidate.get("companyName"),
        candidate.get("supplierName"),
    )

    threshold = (
        config.manufacturer_match_threshold
        if hasattr(config, "manufacturer_match_threshold")
        else config.get("manufacturer_match_threshold", 0.85)
    )
    if manufacturer_conflict(query_company, candidate_company, threshold):
        msg = f"Manufacturer conflict: {query_company} vs {candidate_company}"
        return False, msg
    return True, None


# ── Main acceptance logic ──


def _check_rejections(
    score_query: str,
    candidate: dict[str, Any],
    config: dict[str, Any] | MatchingConfig | None = None,
    skip_components: bool = False,
) -> tuple[bool, str]:
    """Check all rejection criteria and return (is_rejected, reason)."""
    config = config or {}
    checks = [
        _candidate_variant_rejection(score_query, candidate),
        compatibility_rejection_reason(score_query, _candidate_english_name(candidate), config),
    ]
    if not skip_components:
        checks.append(_candidate_component_rejection(score_query, candidate))

    # Check manufacturer mismatch if enabled
    enable_check = (
        config.enable_manufacturer_check
        if hasattr(config, "enable_manufacturer_check")
        else config.get("enable_manufacturer_check", False)
    )
    if enable_check:
        is_ok, reason = _candidate_manufacturer_rejection(
            score_query, candidate, config
        )
        if not is_ok:
            return True, reason or "Manufacturer conflict"

    for reason in checks:
        if reason:
            return True, reason
    return False, ""


def _diagnostic_acceptance(
    score_query: str,
    candidate: dict[str, Any],
    breakdown,
    matching_config,
    skip_components: bool = False,
) -> tuple[bool, str, str]:
    """Return acceptance status and reason text for a candidate."""
    pre_rejection = _candidate_variant_rejection(score_query, candidate)
    if not candidate_has_store_product_id(candidate) and not pre_rejection:
        acceptance = _numeric_acceptance(score_query, candidate, breakdown, matching_config)
        return _orderable_acceptance(candidate, acceptance)

    is_rejected, rejection_reason = _check_rejections(
        score_query, candidate, matching_config, skip_components
    )
    if is_rejected:
        return False, "", rejection_reason

    acceptance = _numeric_acceptance(score_query, candidate, breakdown, matching_config)
    acceptance = _orderable_acceptance(candidate, acceptance)
    return acceptance


def _numeric_acceptance(
    score_query: str,
    candidate: dict[str, Any],
    breakdown,
    matching_config,
) -> tuple[bool, str, str]:
    """Check numeric token acceptance rules."""
    requested = parse_drug(score_query)
    offered = parse_drug(_candidate_english_name(candidate))
    offered.is_synthetic = bool(candidate.get("productNameEnSynthetic"))

    extra_numeric_tokens = _extra_numeric_tokens(score_query, candidate)
    if not extra_numeric_tokens:
        return True, "No extra numeric tokens", ""

    if _any_safe_omission(extra_numeric_tokens, requested, offered):
        return True, "Extra numeric tokens represent safe omission", ""

    return False, "", "unrequested numeric token: storeProductId"


def _extra_numeric_tokens(score_query: str, candidate: dict[str, Any]) -> set[str]:
    """Return numeric tokens in candidate not present in query."""
    query_nums = _numeric_tokens(_normalize_text(score_query))
    candidate_nums = _numeric_tokens(_normalize_text(_candidate_english_name(candidate)))
    return candidate_nums - query_nums


def _iter_results(search_results_by_query):
    """Yield de-duplicated search results with their first query and row index."""
    seen: set[tuple[str, str, str]] = set()
    for query, results in search_results_by_query:
        for row_index, result in enumerate(results):
            key = _candidate_dedupe_key(result)
            if key in seen:
                continue
            seen.add(key)
            yield query, row_index, result


def _candidate_dedupe_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    """Return a stable key for repeated candidates across query variants."""
    return (
        candidate_store_product_id(candidate),
        _normalize_text(_candidate_english_name(candidate)),
        _normalize_text(str(candidate.get("productName") or "")),
    )


__all__ = [
    "_normalize_text",
    "_normalized_tokens",
    "_candidate_component_rejection",
    "_candidate_variant_rejection",
    "_normalized_arabic_name",
    "_synthetic_name_rejection_reasons",
    "_missing_english_identity_reasons",
    "_any_identity_match",
    "_fuzzy_token_match",
    "_identity_tokens",
    "_missing_arabic_token_reasons",
    "_vitacid_c_calcium_conflict",
    "_candidate_manufacturer_rejection",
    "_orderable_acceptance",
    "_any_safe_omission",
    "_safe_omitted_combo_strength",
    "_safe_omitted_topical_strength",
    "_safe_omitted_solid_pack_size",
    "_safe_omitted_injection_volume",
    "_safe_omitted_effervescent_strength",
    "_safe_omitted_liquid_concentration",
    "_safe_omitted_pack_count",
    "_dosage_or_shared_strength",
    "_safe_omitted_pen_insulin_details",
    "_safe_omitted_baby_food_pack_size",
    "_safe_omitted_percentage_concentration",
    "_numeric_tokens",
    "_diagnostic_acceptance",
    "_numeric_acceptance",
    "_extra_numeric_tokens",
    "_iter_results",
    "_candidate_dedupe_key",
]
