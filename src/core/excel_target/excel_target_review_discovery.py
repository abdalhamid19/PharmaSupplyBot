"""Offline, review-only discovery of plausible Excel-target rows.

This module deliberately stops before the verified matching decision.  It only
finds rows from the currently loaded target catalog that are close enough for a
human to inspect.  It does not import or call a translation provider, Cohere,
Tawreed, or any other network service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from src.core.utils.excel import Item

from .excel_target_identity import normalize_arabic_brand, normalize_english_brand
from .excel_target_loader import TargetProduct
from .product_attributes import validate_product_compatibility


ReviewStrategy = Literal["english_fuzzy", "arabic_fuzzy"]
ReviewStatus = Literal[
    "strong",
    "medium",
    "ambiguous",
    "variant_conflict",
    "variant_unproven",
]


@dataclass(frozen=True)
class ReviewDiscoveryConfig:
    """Conservative gates for review-only catalog discovery."""

    enabled: bool = True
    limit: int = 5
    strong_score: float = 90.0
    strong_margin: float = 8.0
    medium_score: float = 86.0
    medium_margin: float = 12.0
    ambiguous_score: float = 88.0
    ambiguous_margin: float = 8.0


@dataclass(frozen=True)
class ReviewDiscoveryHit:
    """One target row retained for human review.

    The product is always a row from the catalog passed to :meth:`build`.
    ``score`` and the other fields are evidence only; callers must not use this
    object as a verified match.
    """

    product: TargetProduct
    score: float
    runner_up_score: float
    score_margin: float
    strategy: ReviewStrategy
    review_status: ReviewStatus
    shared_brand_tokens: tuple[str, ...]
    attribute_note: str

    @property
    def target_row_key(self) -> tuple[str, str, int, str]:
        """Return the stable row-aware identity for persistence adapters."""
        return _target_row_identity(self.product)


@dataclass(frozen=True)
class _CatalogEntry:
    product: TargetProduct
    normalized_name: str
    tokens: tuple[str, ...]
    strategy: ReviewStrategy

    @property
    def row_identity(self) -> tuple[str, str, int, str]:
        return _target_row_identity(self.product)


_ScoredCandidate = tuple[_CatalogEntry, float, tuple[str, ...]]
_SelectedCandidate = tuple[_CatalogEntry, float, float, float, tuple[str, ...]]


@dataclass(frozen=True)
class ExcelTargetReviewDiscoveryIndex:
    """Immutable English/Arabic projections over loaded target rows."""

    _english_entries: tuple[_CatalogEntry, ...]
    _arabic_entries: tuple[_CatalogEntry, ...]

    @classmethod
    def build(cls, catalog: Sequence[TargetProduct]) -> "ExcelTargetReviewDiscoveryIndex":
        """Build an offline index while preserving distinct target rows.

        A repeated copy of the same physical row is removed, but the same
        product code on different rows is retained because those rows may be
        different variants.  The row identity includes source file, source
        row, and name in addition to the product id.
        """
        seen_rows: set[tuple[str, str, int, str]] = set()
        english: list[_CatalogEntry] = []
        arabic: list[_CatalogEntry] = []

        for product in catalog:
            row_identity = _target_row_identity(product)
            if row_identity in seen_rows:
                continue
            seen_rows.add(row_identity)

            english_value = product.trusted_name_en
            if english_value:
                normalized = normalize_english_brand(english_value)
                if normalized:
                    english.append(
                        _CatalogEntry(
                            product=product,
                            normalized_name=normalized,
                            tokens=tuple(normalized.split()),
                            strategy="english_fuzzy",
                        )
                    )

            arabic_value = product.name_ar
            if _contains_arabic(arabic_value):
                normalized = normalize_arabic_brand(arabic_value)
                if normalized:
                    arabic.append(
                        _CatalogEntry(
                            product=product,
                            normalized_name=normalized,
                            tokens=tuple(normalized.split()),
                            strategy="arabic_fuzzy",
                        )
                    )

        return cls(
            _english_entries=tuple(sorted(english, key=_entry_sort_key)),
            _arabic_entries=tuple(sorted(arabic, key=_entry_sort_key)),
        )

    def discover(
        self,
        item: Item,
        *,
        config: ReviewDiscoveryConfig,
    ) -> tuple[ReviewDiscoveryHit, ...]:
        """Return deterministic, review-only candidates for ``item``.

        The query chooses exactly one language projection.  This prevents a
        fuzzy comparison from treating an Arabic name as an English name or
        vice versa.  All retained rows are subsequently checked for variant
        diagnostics, but an attribute conflict never removes a brand-qualified
        human candidate.
        """
        if not config.enabled or config.limit <= 0:
            return ()

        projection = _query_projection(item.name)
        if projection is None:
            return ()
        strategy, normalized_query = projection
        entries = self._entries_for(strategy)
        scored = _score_entries(normalized_query, entries, config)
        selection = _select_scored_candidates(scored, config)
        if selection is None:
            return ()
        selected, base_status = selection
        return tuple(
            _build_discovery_hit(
                item,
                entry,
                score,
                runner_up_score,
                score_margin,
                base_status,
                shared_tokens,
            )
            for entry, score, runner_up_score, score_margin, shared_tokens in selected[
                : max(0, int(config.limit))
            ]
        )

    def _entries_for(self, strategy: ReviewStrategy) -> tuple[_CatalogEntry, ...]:
        return self._arabic_entries if strategy == "arabic_fuzzy" else self._english_entries


def _query_projection(raw_name: str) -> tuple[ReviewStrategy, str] | None:
    if _contains_arabic(raw_name):
        normalized = normalize_arabic_brand(raw_name)
        return ("arabic_fuzzy", normalized) if normalized else None
    normalized = normalize_english_brand(raw_name)
    return ("english_fuzzy", normalized) if normalized else None


def _score_entries(
    normalized_query: str,
    entries: Sequence[_CatalogEntry],
    config: ReviewDiscoveryConfig,
) -> list[_ScoredCandidate]:
    query_tokens = tuple(normalized_query.split())
    minimum_score = min(config.medium_score, config.ambiguous_score)
    scored: list[_ScoredCandidate] = []
    for entry in entries:
        shared_tokens = _shared_brand_tokens(query_tokens, entry.tokens)
        score = float(fuzz.ratio(normalized_query, entry.normalized_name))
        if shared_tokens and score >= minimum_score:
            scored.append((entry, score, shared_tokens))
    return sorted(scored, key=_scored_sort_key)


def _select_scored_candidates(
    scored: Sequence[_ScoredCandidate],
    config: ReviewDiscoveryConfig,
) -> tuple[tuple[_SelectedCandidate, ...], ReviewStatus] | None:
    if not scored:
        return None
    top_entry, top_score, top_tokens = scored[0]
    runner_up_score = scored[1][1] if len(scored) > 1 else 0.0
    top_margin = top_score - runner_up_score

    if _is_ambiguous(scored, config):
        first, second = scored[:2]
        score_margin = abs(first[1] - second[1])
        selected = (
            (first[0], first[1], second[1], score_margin, first[2]),
            (second[0], second[1], first[1], score_margin, second[2]),
        )
        return selected, "ambiguous"
    if top_score >= config.strong_score and top_margin >= config.strong_margin:
        selected = ((top_entry, top_score, runner_up_score, top_margin, top_tokens),)
        return selected, "strong"
    if _is_medium(scored, config):
        selected = ((top_entry, top_score, runner_up_score, top_margin, top_tokens),)
        return selected, "medium"
    return None


def _build_discovery_hit(
    item: Item,
    entry: _CatalogEntry,
    score: float,
    runner_up_score: float,
    score_margin: float,
    base_status: ReviewStatus,
    shared_tokens: tuple[str, ...],
) -> ReviewDiscoveryHit:
    compatibility = validate_product_compatibility(item.name, entry.product.name_ar)
    return ReviewDiscoveryHit(
        product=entry.product,
        score=score,
        runner_up_score=runner_up_score,
        score_margin=score_margin,
        strategy=entry.strategy,
        review_status=_status_for_compatibility(base_status, compatibility.rejection_reason),
        shared_brand_tokens=shared_tokens,
        attribute_note=compatibility.rejection_reason,
    )


def _contains_arabic(value: str) -> bool:
    return any("\u0600" <= character <= "\u06ff" for character in (value or ""))


def _target_row_identity(product: TargetProduct) -> tuple[str, str, int, str]:
    return (
        product.store_product_id,
        product.source_file,
        int(product.source_row_number or 0),
        product.name,
    )


def _entry_sort_key(entry: _CatalogEntry) -> tuple[str, str, int, str]:
    product = entry.product
    return (
        str(product.store_product_id).casefold(),
        str(product.source_file).casefold(),
        int(product.source_row_number or 0),
        str(product.name).casefold(),
    )


def _scored_sort_key(
    scored: _ScoredCandidate,
) -> tuple[float, int, int, tuple[str, str, int, str]]:
    entry, score, shared_tokens = scored
    return (
        -score,
        -len(shared_tokens),
        -sum(len(token) for token in shared_tokens),
        _entry_sort_key(entry),
    )


def _shared_brand_tokens(
    query_tokens: Sequence[str], candidate_tokens: Sequence[str]
) -> tuple[str, ...]:
    """Return meaningful exact or one-edit brand anchors from the query."""
    query_meaningful = [token for token in query_tokens if _meaningful_brand_token(token)]
    candidate_meaningful = [
        token for token in candidate_tokens if _meaningful_brand_token(token)
    ]
    exact = _exact_shared_tokens(query_meaningful, candidate_meaningful)
    near = _near_shared_tokens(query_meaningful, candidate_meaningful, exact)
    return tuple(dict.fromkeys((*exact, *near)))


def _exact_shared_tokens(
    query_tokens: Sequence[str], candidate_tokens: Sequence[str]
) -> tuple[str, ...]:
    candidate_set = set(candidate_tokens)
    return tuple(token for token in query_tokens if token in candidate_set)


def _near_shared_tokens(
    query_tokens: Sequence[str],
    candidate_tokens: Sequence[str],
    exact_tokens: Sequence[str],
) -> tuple[str, ...]:
    near: list[str] = []
    for query_token in query_tokens:
        if query_token in exact_tokens or len(query_token) < 6:
            continue
        if any(
            len(candidate_token) >= 6
            and Levenshtein.distance(query_token, candidate_token) <= 1
            for candidate_token in candidate_tokens
        ):
            near.append(query_token)
    return tuple(near)


_GENERIC_BRAND_TOKENS = frozenset(
    {
        "A",
        "AB",
        "AND",
        "CO",
        "C",
        "DUO",
        "F",
        "FORTE",
        "MEN",
        "NIGHT",
        "PLUS",
        "TRIO",
        "VITAMIN",
        "WOMEN",
        "XR",
        "بلس",
        "رجال",
        "سيدات",
        "فيتامين",
        "وومن",
    }
)


_PRESENTATION_TOKENS = frozenset(
    {
        "AMP",
        "AMPOULE",
        "AMPOULES",
        "CAP",
        "CAPS",
        "CAPSULE",
        "CAPSULES",
        "CREAM",
        "DROPS",
        "FILM",
        "FILMS",
        "GEL",
        "INJ",
        "INJECTION",
        "LOTION",
        "LOZENGE",
        "ML",
        "MG",
        "OINT",
        "OINTMENT",
        "POWDER",
        "SACHET",
        "SPRAY",
        "SUPP",
        "SUPPOSITORY",
        "SUSP",
        "SUSPENSION",
        "SYRUP",
        "TAB",
        "TABLET",
        "TABLETS",
        "TABS",
        "VIAL",
        "VIALS",
        "قرص",
        "اقراص",
        "أقراص",
        "كبسول",
        "كبسولة",
        "كبسولات",
        "شراب",
        "معلق",
        "معلقة",
        "كريم",
        "مرهم",
        "حقن",
        "نقط",
        "قطرة",
        "قطرات",
    }
)


def _meaningful_brand_token(token: str) -> bool:
    folded = token.casefold()
    upper = token.upper()
    is_generic = upper in _PRESENTATION_TOKENS or upper in _GENERIC_BRAND_TOKENS
    if folded.isdigit() or is_generic:
        return False
    if any(character.isalpha() for character in token) and any(
        character.isdigit() for character in token
    ):
        return True
    if len(token) >= 4:
        return True
    return len(token) >= 6


def _is_ambiguous(
    scored: Sequence[tuple[_CatalogEntry, float, tuple[str, ...]]],
    config: ReviewDiscoveryConfig,
) -> bool:
    if len(scored) < 2:
        return False
    top_score = scored[0][1]
    runner_up_score = scored[1][1]
    return (
        top_score >= config.ambiguous_score
        and runner_up_score >= config.ambiguous_score
        and top_score - runner_up_score < config.ambiguous_margin
    )


def _is_medium(
    scored: Sequence[tuple[_CatalogEntry, float, tuple[str, ...]]],
    config: ReviewDiscoveryConfig,
) -> bool:
    if not scored:
        return False
    _, top_score, shared_tokens = scored[0]
    runner_up_score = scored[1][1] if len(scored) > 1 else 0.0
    medium_candidates = sum(score >= config.medium_score for _, score, _ in scored)
    return (
        top_score >= config.medium_score
        and top_score - runner_up_score >= config.medium_margin
        and medium_candidates == 1
        and any(len(token) >= 6 for token in shared_tokens)
    )


def _status_for_compatibility(base_status: ReviewStatus, reason: str) -> ReviewStatus:
    if not reason:
        return base_status
    if "not proven" in reason:
        return "variant_unproven"
    return "variant_conflict"


__all__ = [
    "ExcelTargetReviewDiscoveryIndex",
    "ReviewDiscoveryConfig",
    "ReviewDiscoveryHit",
]
