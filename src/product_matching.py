"""Product query generation and fuzzy matching helpers for Tawreed search results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Iterable

from .config import MatchingConfig
from .excel import Item


@dataclass(frozen=True)
class _SearchMatch:
    query: str
    row_index: int
    score: float
    data: dict[str, Any]


@dataclass(frozen=True)
class MatchScoreBreakdown:
    sequence_score: float
    overlap_score: float
    numeric_overlap: float
    exact_bonus: float
    availability_bonus: float
    total_score: float


@dataclass(frozen=True)
class CandidateMatchDiagnostic:
    query: str
    row_index: int
    score: float
    sort_key: tuple[float, int, float, int, int, int]
    accepted: bool
    accepted_reason: str
    rejection_reason: str
    breakdown: MatchScoreBreakdown
    candidate: dict[str, Any]


@dataclass(frozen=True)
class MatchDecision:
    best_match: _SearchMatch | None
    diagnostics: list[CandidateMatchDiagnostic]
    final_reason: str


def _normalize_text(value: str) -> str:
    """Normalize product text so Arabic and English matching stay numerically stable."""
    text = str(value or "").upper()
    text = re.sub(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _token_overlap_score(query: str, candidate: str) -> float:
    """Measure how much the candidate tokens overlap the query tokens."""
    query_tokens = _normalize_text(query).split()
    candidate_tokens = _normalize_text(candidate).split()
    if not query_tokens or not candidate_tokens:
        return 0.0

    total_score = 0.0
    for query_token in query_tokens:
        total_score += _best_token_score(query_token, candidate_tokens)
    return total_score / len(query_tokens)


def _match_score(query: str, candidate: dict[str, Any]) -> float:
    """Score a Tawreed search result against the requested Excel item text."""
    return _match_score_breakdown(query, candidate).total_score


def _match_score_breakdown(query: str, candidate: dict[str, Any]) -> MatchScoreBreakdown:
    """Return the detailed score breakdown for one Tawreed search result."""
    candidate_texts = _candidate_texts(candidate)
    if not candidate_texts:
        return MatchScoreBreakdown(
            sequence_score=0.0,
            overlap_score=0.0,
            numeric_overlap=0.0,
            exact_bonus=0.0,
            availability_bonus=-999.0,
            total_score=-999.0,
        )

    query_text = query or ""
    normalized_query = _normalize_text(query_text)
    sequence_score = _best_sequence_score(normalized_query, candidate_texts)
    overlap_score = _best_overlap_score(query_text, candidate_texts)
    numeric_overlap = _numeric_overlap_score(normalized_query, candidate_texts)
    exact_bonus = _exact_or_contained_bonus(normalized_query, candidate_texts)
    availability_bonus = _availability_bonus(candidate)
    total_score = (
        (sequence_score * 5.0)
        + (overlap_score * 8.0)
        + (numeric_overlap * 6.0)
        + exact_bonus
        + availability_bonus
    )
    return MatchScoreBreakdown(
        sequence_score=sequence_score,
        overlap_score=overlap_score,
        numeric_overlap=numeric_overlap,
        exact_bonus=exact_bonus,
        availability_bonus=availability_bonus,
        total_score=total_score,
    )


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
    accepted, _, _ = _acceptance_details(query, candidate, score, _default_matching_config())
    return accepted


def _acceptance_details(
    query: str,
    candidate: dict[str, Any],
    score: float,
    matching_config: MatchingConfig,
) -> tuple[bool, str, str]:
    """Return whether a match is acceptable plus acceptance and rejection reasons."""
    normalized_query = _normalize_text(query)
    normalized_english_name = _normalize_text(_candidate_english_name(candidate))
    best_overlap = _best_candidate_overlap(query, candidate)
    has_numeric_match = _numeric_match_count(normalized_query, normalized_english_name) > 0
    if matching_config.exact_match_accept and normalized_query and normalized_query == normalized_english_name:
        return True, "exact_normalized_name_match", ""
    if best_overlap >= matching_config.high_overlap_threshold:
        return True, "high_token_overlap", ""
    if score >= matching_config.medium_score_threshold and best_overlap >= matching_config.medium_overlap_threshold:
        return True, "strong_score_with_good_overlap", ""
    if (
        score >= matching_config.numeric_score_threshold
        and has_numeric_match
        and best_overlap >= matching_config.numeric_overlap_threshold
    ):
        return True, "strong_score_with_numeric_match", ""
    rejection_reason = (
        f"Rejected: overlap={best_overlap:.3f}, score={score:.3f}, "
        f"numeric_match={has_numeric_match}, exact_name={bool(normalized_query and normalized_query == normalized_english_name)}"
    )
    return False, "", rejection_reason


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
    tokens = name.split()
    return _unique_non_empty(
        [
            name,
            " ".join(tokens[:4]),
            " ".join(tokens[:3]),
            " ".join(tokens[:2]),
            tokens[0] if tokens else "",
        ]
    )


def find_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> _SearchMatch | None:
    """Return the highest-ranked acceptable search result across all generated queries."""
    return explain_best_product_match(item, search_results_by_query, matching_config).best_match


def explain_best_product_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig | None = None,
) -> MatchDecision:
    """Return the best match plus diagnostics for every candidate considered."""
    active_matching_config = matching_config or _default_matching_config()
    diagnostics = _build_candidate_diagnostics(item, search_results_by_query, active_matching_config)
    if not diagnostics:
        return MatchDecision(best_match=None, diagnostics=[], final_reason="No search candidates were returned.")
    best_diagnostic = max(diagnostics, key=lambda diagnostic: diagnostic.sort_key)
    if not best_diagnostic.accepted:
        return MatchDecision(
            best_match=None,
            diagnostics=diagnostics,
            final_reason=best_diagnostic.rejection_reason or "Best candidate was rejected by acceptance rules.",
        )
    return MatchDecision(
        best_match=_SearchMatch(
            query=best_diagnostic.query,
            row_index=best_diagnostic.row_index,
            score=best_diagnostic.score,
            data=best_diagnostic.candidate,
        ),
        diagnostics=diagnostics,
        final_reason=f"Accepted best candidate because {best_diagnostic.accepted_reason}.",
    )


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


def _best_sequence_score(normalized_query: str, candidate_texts: Iterable[str]) -> float:
    """Return the best sequence similarity against all candidate names."""
    return max(
        SequenceMatcher(None, normalized_query, candidate_text).ratio()
        for candidate_text in candidate_texts
    )


def _best_overlap_score(query: str, candidate_texts: Iterable[str]) -> float:
    """Return the best token overlap score against all candidate names."""
    return max(
        _token_overlap_score(query, candidate_text)
        for candidate_text in candidate_texts
    )


def _numeric_overlap_score(normalized_query: str, candidate_texts: Iterable[str]) -> float:
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


def _numeric_overlap_ratio(query_numeric_tokens: set[str], candidate_numeric_tokens: set[str]) -> float:
    """Return the fraction of query numeric tokens found in the candidate."""
    return len(query_numeric_tokens & candidate_numeric_tokens) / max(1, len(query_numeric_tokens))


def _exact_or_contained_bonus(normalized_query: str, candidate_texts: Iterable[str]) -> float:
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
    if available_quantity > 0 or products_count > 0 or candidate.get("storeProductId"):
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


def _best_scored_match(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> _SearchMatch | None:
    """Return the highest-ranked scored result across all generated queries."""
    best_match: _SearchMatch | None = None
    best_key: tuple[float, int, float, int, int, int] | None = None
    for query, row_index, result in _iter_results(search_results_by_query):
        score = _match_score(item.name or query, result)
        match = _SearchMatch(
            query=query,
            row_index=row_index,
            score=score,
            data=result,
        )
        match_key = _match_sort_key(item.name or query, result, score)
        if best_match is None or best_key is None or match_key > best_key:
            best_match = match
            best_key = match_key
    return best_match


def _build_candidate_diagnostics(
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
    matching_config: MatchingConfig,
) -> list[CandidateMatchDiagnostic]:
    """Build diagnostics for every search result candidate considered."""
    diagnostics: list[CandidateMatchDiagnostic] = []
    for query, row_index, result in _iter_results(search_results_by_query):
        score_query = item.name or query
        breakdown = _match_score_breakdown(score_query, result)
        accepted, accepted_reason, rejection_reason = _acceptance_details(
            score_query,
            result,
            breakdown.total_score,
            matching_config,
        )
        diagnostics.append(
            CandidateMatchDiagnostic(
                query=query,
                row_index=row_index,
                score=breakdown.total_score,
                sort_key=_match_sort_key(score_query, result, breakdown.total_score),
                accepted=accepted,
                accepted_reason=accepted_reason,
                rejection_reason=rejection_reason,
                breakdown=breakdown,
                candidate=result,
            )
        )
    return diagnostics


def _default_matching_config() -> MatchingConfig:
    """Return the built-in matching thresholds used when no config is supplied."""
    return MatchingConfig()


def _iter_results(
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> Iterable[tuple[str, int, dict[str, Any]]]:
    """Yield each search result with its originating query and row index."""
    for query, results in search_results_by_query:
        for row_index, result in enumerate(results):
            yield query, row_index, result
