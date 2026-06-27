"""Safe omission logic for numeric tokens in product matching."""

from __future__ import annotations

import re
from typing import Any

from .drug_matching.normalizer import parse_drug


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
    topical_forms = {"CREAM", "GEL", "LOTION", "SOLUTION", "SPRAY"}
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
    from .product_matching_scoring import _numeric_tokens

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
