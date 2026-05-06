"""Product query generation and fuzzy matching helpers for Tawreed search results."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable

_OCR_ZERO_RE = re.compile(r"(?<=\d)[Oo](?=\b|[^A-Za-z0-9])")
_TOKEN_BOUNDARY_RE = re.compile(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")
_ARABIC_NON_WORD_RE = re.compile(r"[^\w\u0600-\u06FF]+")
_ARABIC_WHITESPACE_RE = re.compile(r"\s+")
MAX_SEARCH_QUERY_VARIANTS = 24
_ARABIC_REQUIRED_TOKEN_ALIASES = {
    "AR": ("ايه ار", "اي ار", "ارتجاع"),
    "DOUCHE": ("دش", "غسول", "مهبل"),
    "EFF": ("فوار",),
    "LOTION": ("لوشن", "لوسيون"),
    "ML": ("مل", "مللي", "ميللي"),
    "VAG": ("مهبل", "المهبل", "نسائي"),
    "VAGINAL": ("مهبل", "المهبل", "نسائي"),
}
_GENERIC_IDENTITY_TOKENS = {
    "ANTISEPTIC",
    "AMP",
    "AMPS",
    "CAP",
    "CAPS",
    "COUGH",
    "EFF",
    "FLAVOR",
    "FLAVOUR",
    "G",
    "GM",
    "MCG",
    "MG",
    "MILK",
    "ML",
    "O",
    "ORAL",
    "SOLN",
    "SOLUTION",
    "SYRUP",
    "TAB",
    "TABS",
}

from .config.config_models import MatchingConfig
from .matching_models import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
    SearchMatch,
)
from .matching_rules import acceptance_details, default_matching_config
from .utils.excel import Item


def _normalize_text(value: str) -> str:
    """Normalize product text so Arabic and English matching stay stable."""
    text = _OCR_ZERO_RE.sub("0", str(value or "")).upper()
    text = _TOKEN_BOUNDARY_RE.sub(" ", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _normalized_tokens(value: str) -> list[str]:
    """Return normalized tokens for a search term or candidate name."""
    return _normalize_text(value).split()


def _token_overlap_score(query: str, candidate: str) -> float:
    """Measure how much the candidate tokens overlap the query tokens."""
    query_tokens = _normalized_tokens(query)
    candidate_tokens = _normalized_tokens(candidate)
    if not query_tokens or not candidate_tokens:
        return 0.0

    total_score = 0.0
    for query_token in query_tokens:
        total_score += _best_token_score(query_token, candidate_tokens)
    return total_score / len(query_tokens)


def _match_score(query: str, candidate: dict[str, Any]) -> float:
    """Score a Tawreed search result against the requested Excel item text."""
    return _match_score_breakdown(query, candidate).total_score


def _match_score_breakdown(
    query: str, candidate: dict[str, Any]
) -> MatchScoreBreakdown:
    """Return the detailed score breakdown for one Tawreed search result."""
    candidate_texts = _candidate_texts(candidate)
    if not candidate_texts:
        return _empty_breakdown()

    return _scored_breakdown(query, candidate, candidate_texts)


def _match_sort_key(
    query: str,
    candidate: dict[str, Any],
    score: float,
) -> tuple[float, int, float, int, int, int]:
    """Build a stable sort key for choosing the best search match."""
    normalized_query = _normalize_text(query)
    normalized_english_name = _normalize_text(_candidate_english_name(candidate))
    return (
        score,
        int(normalized_query == normalized_english_name),
        _token_overlap_score(query, _candidate_english_name(candidate)),
        _numeric_match_count(normalized_query, normalized_english_name),
        int(candidate.get("productsCount") or 0),
        int(candidate.get("availableQuantity") or 0),
    )


def _is_match_acceptable(query: str, candidate: dict[str, Any], score: float) -> bool:
    """Apply acceptance thresholds before a match is allowed to drive ordering."""
    accepted, _, _ = _acceptance_details(
        query,
        candidate,
        score,
        default_matching_config(),
    )
    return accepted


def _acceptance_details(
    query: str,
    candidate: dict[str, Any],
    score: float,
    matching_config: MatchingConfig,
) -> tuple[bool, str, str]:
    """Return whether a match is acceptable plus acceptance and rejection reasons."""
    return acceptance_details(
        query,
        candidate,
        score,
        matching_config,
        _matching_rule_helpers(),
    )


def _unique_non_empty(values: list[str]) -> list[str]:
    """Remove empty values and duplicates while preserving query order."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _search_queries_for_item(item: Item) -> list[str]:
    """Build ordered search queries from the Excel item name and code."""
    name = str(item.name or "").strip()
    normalized_name = _normalize_search_query(name)
    tokens = name.split()
    normalized_tokens = normalized_name.split()
    queries = _priority_search_queries(name, normalized_name, tokens, normalized_tokens)
    queries.extend(_fallback_search_queries(item.code, tokens, normalized_tokens))
    return _unique_non_empty(queries)[:MAX_SEARCH_QUERY_VARIANTS]


def _priority_search_queries(
    name: str, normalized_name: str, tokens: list[str], normalized_tokens: list[str]
) -> list[str]:
    """Return high-signal full-name and leading-token query variants."""
    return [
        name,
        normalized_name,
        " ".join(tokens[:4]),
        " ".join(normalized_tokens[:4]),
        " ".join(tokens[:3]),
        " ".join(normalized_tokens[:3]),
        " ".join(tokens[:2]),
        " ".join(normalized_tokens[:2]),
        tokens[0] if tokens else "",
        normalized_tokens[0] if normalized_tokens else "",
    ]


def _fallback_search_queries(
    code: object, tokens: list[str], normalized_tokens: list[str]
) -> list[str]:
    """Return extra bounded fallback queries when priority variants do not match."""
    fallback = [_normalized_item_code(code)]
    fallback.extend(_token_window_queries(normalized_tokens or tokens, window_size=2))
    fallback.extend(normalized_tokens or tokens)
    return fallback


def _token_window_queries(tokens: list[str], window_size: int) -> list[str]:
    """Return contiguous token-window query variants."""
    if len(tokens) <= window_size:
        return []
    return [
        " ".join(tokens[index : index + window_size])
        for index in range(1, len(tokens) - window_size + 1)
    ]


def _normalized_item_code(code: object) -> str:
    """Return a code search query when the Excel item code looks usable."""
    text = str(code or "").strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def _normalize_search_query(value: str) -> str:
    """Return a search-friendly variant that separates dosage and punctuation tokens."""
    return _normalize_text(value)


def find_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> SearchMatch | None:
    """Return the highest-ranked acceptable search result across all generated queries."""
    return explain_best_product_match(
        item, search_results_by_query, matching_config
    ).best_match


def explain_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> MatchDecision:
    """Return the best match plus diagnostics for every candidate considered."""
    active_matching_config = matching_config or default_matching_config()
    diagnostics = _build_candidate_diagnostics(
        item,
        search_results_by_query,
        active_matching_config,
    )
    return _decision_from_diagnostics(diagnostics)


def is_decisive_product_match(query: str, candidate: dict[str, Any]) -> bool:
    """Return whether the candidate is an exact normalized name match for the query."""
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return False
    return normalized_query in _candidate_texts(candidate)


def _best_token_score(query_token: str, candidate_tokens: list[str]) -> float:
    """Return the best overlap score for one query token."""
    best_score = 0.0
    for candidate_token in candidate_tokens:
        if query_token == candidate_token:
            return 1.0
        if query_token in candidate_token or candidate_token in query_token:
            best_score = max(best_score, 0.7)
    return best_score


def _candidate_texts(candidate: dict[str, Any]) -> list[str]:
    """Return normalized English and Arabic candidate names."""
    english_name = _normalize_text(_candidate_english_name(candidate))
    arabic_name = _normalize_text(str(candidate.get("productName") or ""))
    return [text for text in (english_name, arabic_name) if text]


def _candidate_english_name(candidate: dict[str, Any]) -> str:
    """Return the raw English candidate name."""
    return str(candidate.get("productNameEn") or "")


def _best_sequence_score(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return the best sequence similarity against all candidate names."""
    return max(
        SequenceMatcher(None, normalized_query, candidate_text).ratio()
        for candidate_text in candidate_texts
    )


def _best_overlap_score(normalized_query: str, candidate_texts: Iterable[str]) -> float:
    """Return the best token overlap score against all candidate names."""
    if not normalized_query:
        return 0.0
    return max(
        _token_overlap_score(normalized_query, candidate_text)
        for candidate_text in candidate_texts
    )


def _numeric_overlap_score(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return how well numeric tokens in the query appear in candidate names."""
    query_numeric_tokens = _numeric_tokens(normalized_query)
    if not query_numeric_tokens:
        return 0.0

    numeric_scores = [
        _numeric_overlap_ratio(query_numeric_tokens, _numeric_tokens(candidate_text))
        for candidate_text in candidate_texts
    ]
    return max(numeric_scores, default=0.0)


def _numeric_tokens(text: str) -> set[str]:
    """Return tokens that contain at least one digit."""
    return {
        token
        for token in text.split()
        if any(character.isdigit() for character in token)
    }


def _numeric_overlap_ratio(
    query_numeric_tokens: set[str],
    candidate_numeric_tokens: set[str],
) -> float:
    """Return the fraction of query numeric tokens found in the candidate."""
    return len(query_numeric_tokens & candidate_numeric_tokens) / max(
        1, len(query_numeric_tokens)
    )


def _exact_or_contained_bonus(
    normalized_query: str, candidate_texts: Iterable[str]
) -> float:
    """Return the exact-match bonus when one text strongly contains the other."""
    if not normalized_query:
        return 0.0
    if any(
        normalized_query == candidate_text
        or normalized_query in candidate_text
        or candidate_text in normalized_query
        for candidate_text in candidate_texts
    ):
        return 2.0
    return 0.0


def _availability_bonus(candidate: dict[str, Any]) -> float:
    """Return a small score bonus or penalty based on availability signals."""
    available_quantity = int(candidate.get("availableQuantity") or 0)
    products_count = int(candidate.get("productsCount") or 0)
    if available_quantity > 0 or products_count > 0:
        return 1.0
    return -1.5


def _numeric_match_count(normalized_query: str, normalized_name: str) -> int:
    """Return how many numeric tokens the query and candidate share."""
    return len(_numeric_tokens(normalized_query) & _numeric_tokens(normalized_name))


def _best_candidate_overlap(query: str, candidate: dict[str, Any]) -> float:
    """Return the best overlap score across English and Arabic names."""
    return max(
        _token_overlap_score(query, _candidate_english_name(candidate)),
        _token_overlap_score(query, str(candidate.get("productName") or "")),
    )


def _build_candidate_diagnostics(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig,
) -> list[CandidateMatchDiagnostic]:
    """Build diagnostics for every search result candidate considered."""
    diagnostics: list[CandidateMatchDiagnostic] = []
    for query, row_index, result in _iter_results(search_results_by_query):
        diagnostics.append(
            _candidate_diagnostic(
                item.name or query,
                query,
                row_index,
                result,
                matching_config,
            )
        )
    return diagnostics


def _empty_breakdown() -> MatchScoreBreakdown:
    """Return the breakdown used when a candidate has no usable names."""
    return MatchScoreBreakdown(
        sequence_score=0.0,
        overlap_score=0.0,
        numeric_overlap=0.0,
        exact_bonus=0.0,
        availability_bonus=-999.0,
        total_score=-999.0,
    )


def _scored_breakdown(
    query: str,
    candidate: dict[str, Any],
    candidate_texts: list[str],
) -> MatchScoreBreakdown:
    """Return the weighted scoring breakdown for one usable candidate."""
    score_components = _score_components(query, candidate, candidate_texts)
    return MatchScoreBreakdown(
        sequence_score=score_components["sequence_score"],
        overlap_score=score_components["overlap_score"],
        numeric_overlap=score_components["numeric_overlap"],
        exact_bonus=score_components["exact_bonus"],
        availability_bonus=score_components["availability_bonus"],
        total_score=_total_score(**score_components),
    )


def _score_components(
    query: str,
    candidate: dict[str, Any],
    candidate_texts: list[str],
) -> dict[str, float]:
    """Return the raw score components for one usable candidate."""
    normalized_query = _normalize_text(query or "")
    return {
        "sequence_score": _best_sequence_score(normalized_query, candidate_texts),
        "overlap_score": _best_overlap_score(normalized_query, candidate_texts),
        "numeric_overlap": _numeric_overlap_score(normalized_query, candidate_texts),
        "exact_bonus": _exact_or_contained_bonus(normalized_query, candidate_texts),
        "availability_bonus": _availability_bonus(candidate),
    }


def _total_score(
    sequence_score: float,
    overlap_score: float,
    numeric_overlap: float,
    exact_bonus: float,
    availability_bonus: float,
) -> float:
    """Return the weighted final score for one candidate."""
    return (
        (sequence_score * 5.0)
        + (overlap_score * 8.0)
        + (numeric_overlap * 6.0)
        + exact_bonus
        + availability_bonus
    )


def _decision_from_diagnostics(
    diagnostics: list[CandidateMatchDiagnostic],
) -> MatchDecision:
    """Return the final match decision for an already-scored diagnostic list."""
    if not diagnostics:
        return _empty_match_decision()
    sorted_diagnostics = sorted(
        diagnostics, key=lambda diagnostic: diagnostic.sort_key, reverse=True
    )
    best_accepted = _best_accepted_diagnostic(sorted_diagnostics)
    if best_accepted is None:
        return _rejected_match_decision(diagnostics, sorted_diagnostics[0])
    return _accepted_match_decision(diagnostics, best_accepted)


def _empty_match_decision() -> MatchDecision:
    """Return the no-candidates match decision."""
    return MatchDecision(
        best_match=None,
        diagnostics=[],
        final_reason="No search candidates were returned.",
    )


def _rejected_match_decision(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> MatchDecision:
    """Return a rejected match decision for the highest-ranked candidate."""
    return MatchDecision(
        best_match=None,
        diagnostics=diagnostics,
        final_reason=_rejected_decision_reason(best_diagnostic),
    )


def _accepted_match_decision(
    diagnostics: list[CandidateMatchDiagnostic],
    best_diagnostic: CandidateMatchDiagnostic,
) -> MatchDecision:
    """Return an accepted match decision for the highest-ranked accepted row."""
    return MatchDecision(
        best_match=_search_match(best_diagnostic),
        diagnostics=diagnostics,
        final_reason=_accepted_decision_reason(best_diagnostic),
    )


def _best_accepted_diagnostic(
    diagnostics: list[CandidateMatchDiagnostic],
) -> CandidateMatchDiagnostic | None:
    """Return the highest-ranked accepted diagnostic, if any."""
    for diagnostic in diagnostics:
        if diagnostic.accepted:
            return diagnostic
    return None


def _rejected_decision_reason(best_diagnostic: CandidateMatchDiagnostic) -> str:
    """Return the message used when the best candidate fails acceptance rules."""
    return (
        best_diagnostic.rejection_reason
        or "Best candidate was rejected by acceptance rules."
    )


def _accepted_decision_reason(best_diagnostic: CandidateMatchDiagnostic) -> str:
    """Return the message used when the best candidate passes acceptance rules."""
    return f"Accepted best candidate because {best_diagnostic.accepted_reason}."


def _search_match(diagnostic: CandidateMatchDiagnostic) -> SearchMatch:
    """Return the public search-match object for one accepted diagnostic."""
    return SearchMatch(
        query=diagnostic.query,
        row_index=diagnostic.row_index,
        score=diagnostic.score,
        data=diagnostic.candidate,
    )


def _candidate_diagnostic(
    score_query: str,
    query: str,
    row_index: int,
    result: dict[str, Any],
    matching_config: MatchingConfig,
) -> CandidateMatchDiagnostic:
    """Return one diagnostic record for a candidate result row."""
    breakdown = _match_score_breakdown(score_query, result)
    acceptance = _diagnostic_acceptance(score_query, result, breakdown, matching_config)
    return _diagnostic_record(
        query, row_index, result, score_query, breakdown, acceptance
    )


def _diagnostic_record(
    query: str,
    row_index: int,
    result: dict[str, Any],
    score_query: str,
    breakdown: MatchScoreBreakdown,
    acceptance: tuple[bool, str, str],
) -> CandidateMatchDiagnostic:
    """Return the final diagnostic dataclass for one candidate result row."""
    return CandidateMatchDiagnostic(
        query=query,
        row_index=row_index,
        score=breakdown.total_score,
        sort_key=_match_sort_key(score_query, result, breakdown.total_score),
        accepted=acceptance[0],
        accepted_reason=acceptance[1],
        rejection_reason=acceptance[2],
        breakdown=breakdown,
        candidate=result,
    )


def _diagnostic_acceptance(
    score_query: str,
    result: dict[str, Any],
    breakdown: MatchScoreBreakdown,
    matching_config: MatchingConfig,
) -> tuple[bool, str, str]:
    """Return the acceptance outcome for one candidate diagnostic."""
    variant_rejection = _candidate_variant_rejection(score_query, result)
    if variant_rejection:
        return False, "", variant_rejection
    return _acceptance_details(
        score_query,
        result,
        breakdown.total_score,
        matching_config,
    )


def _candidate_variant_rejection(query: str, candidate: dict[str, Any]) -> str:
    """Return a rejection reason when Arabic names contradict key query tokens."""
    arabic_name = _normalized_arabic_name(candidate)
    if not arabic_name:
        return ""
    query_tokens = set(_normalized_tokens(query))
    reasons = _synthetic_name_rejection_reasons(query_tokens, candidate)
    reasons.extend(_missing_arabic_token_reasons(query_tokens, arabic_name))
    if _vitacid_c_calcium_conflict(query_tokens, arabic_name):
        reasons.append("Arabic name contains calcium for VITACID C query")
    return "; ".join(reasons)


def _normalized_arabic_name(candidate: dict[str, Any]) -> str:
    """Return a whitespace-normalized Arabic candidate name."""
    raw_name = str(candidate.get("productName") or "").strip()
    spaced_name = _ARABIC_NON_WORD_RE.sub(" ", raw_name)
    return _ARABIC_WHITESPACE_RE.sub(" ", spaced_name).strip()


def _synthetic_name_rejection_reasons(
    query_tokens: set[str], candidate: dict[str, Any]
) -> list[str]:
    """Return rejection reasons when a synthetic English name is too generic."""
    if not candidate.get("productNameEnSynthetic"):
        return []
    candidate_tokens = set(_normalized_tokens(_candidate_english_name(candidate)))
    identity_tokens = _identity_tokens(query_tokens)
    if identity_tokens and not identity_tokens & candidate_tokens:
        return ["Synthetic English name missing requested identity token"]
    return []


def _identity_tokens(tokens: set[str]) -> set[str]:
    """Return non-generic tokens that should identify the requested product."""
    return {
        token
        for token in tokens
        if len(token) > 1
        and not token.isdigit()
        and token not in _GENERIC_IDENTITY_TOKENS
    }


def _missing_arabic_token_reasons(tokens: set[str], arabic_name: str) -> list[str]:
    """Return reasons for required query tokens missing from the Arabic name."""
    reasons: list[str] = []
    for token, aliases in _ARABIC_REQUIRED_TOKEN_ALIASES.items():
        if token in tokens and not any(alias in arabic_name for alias in aliases):
            reasons.append(f"Arabic name missing marker for {token}")
    return reasons


def _vitacid_c_calcium_conflict(tokens: set[str], arabic_name: str) -> bool:
    """Return whether a Vitacid-C query was matched to a calcium product."""
    return "VITACID" in tokens and "C" in tokens and "كالسيوم" in arabic_name


def _matching_rule_helpers() -> tuple:
    """Return helper callables used by the acceptance-rules module."""
    return (
        _normalize_text,
        _candidate_english_name,
        _best_candidate_overlap,
        _numeric_match_count,
    )


def _iter_results(
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> Iterable[tuple[str, int, dict[str, Any]]]:
    """Yield each search result with its originating query and row index."""
    for query, results in search_results_by_query:
        for row_index, result in enumerate(results):
            yield query, row_index, result
