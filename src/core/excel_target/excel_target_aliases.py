"""Conservative, offline alias resolution for Excel target products.

This module deliberately stops at candidate generation.  It does not decide
whether a candidate is safe to order: callers must still apply product
attribute compatibility and target-row uniqueness checks.

Built-in aliases are audited ``tawreed``/``egyptian`` entries. Caller-provided
alias entries retain their existing source contract and are still subject to
the resolver's score, margin, compatibility, and target-row gates.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from rapidfuzz import fuzz

from .excel_target_loader import TargetProduct


@dataclass(frozen=True)
class AliasEntry:
    """One local English-to-Arabic alias relation."""

    english: str
    arabic: str
    source: str = "local_alias"


@dataclass(frozen=True)
class AliasCandidate:
    """A high-confidence alias candidate for a real target product.

    ``score`` and ``runner_up_margin`` are evidence only.  The caller must
    perform full form/strength/pack compatibility and uniqueness checks before
    accepting this product.
    """

    product_id: str
    canonical_brand: str
    source: str
    score: float
    runner_up_margin: float


APPROVED_ALIAS_ENTRIES: tuple[AliasEntry, ...] = (
    # P-001: the final ``E`` is a reviewed spelling variant of the local
    # Tawreed/dictionary spelling ``COGICIN``.  The Arabic side is the
    # catalog identity; target-row attributes are deliberately left to the
    # caller's compatibility gate.
    AliasEntry("COGICINE", "كوجيسين", "tawreed"),
    # P-007: this is an explicit, catalog-owner-confirmed bilingual relation.
    # It is intentionally not a general transliteration or word-order rule.
    AliasEntry("HERO BABY LF MILK", "لبن هيرو بيبى ال اف", "egyptian"),
)


_DEFAULT_MIN_SCORE = 96.0
_DEFAULT_MIN_MARGIN = 4.0
_MEANINGFUL_MODIFIERS = frozenset(
    {"PLUS", "DUO", "TRIO", "MEN", "WOMEN", "FORTE", "NIGHT", "XR"}
)
_ATTRIBUTE_TOKENS = frozenset(
    {
        "AMP",
        "AMPOULE",
        "AMPOULES",
        "AEROSOL",
        "CAP",
        "CAPS",
        "CAPSULE",
        "CAPSULES",
        # Abbreviated film-coated tablet notation (F.C.TABS.) is tokenized
        # as standalone F and C after punctuation is removed.
        "C",
        "CREAM",
        "DROPS",
        "FILM",
        "FILMS",
        "FLIM",
        "FLIMS",
        "F",
        "G",
        "GEL",
        "GM",
        "IM",
        "INJ",
        "INJECTION",
        "IU",
        "LOTION",
        "LOZ",
        "LOZENGE",
        "LOZENGES",
        "MCG",
        "MGC",
        "MG",
        "ML",
        "OINT",
        "OINTMENT",
        "ORAL",
        "POWDER",
        "PRE",
        "SACHET",
        "SACHETS",
        "SPRAY",
        "SUPP",
        "SUPPOSITORY",
        "SUPPOSITORIES",
        "SOLUTION",
        "SUSP",
        "SUSPENSION",
        "SYRUP",
        "TAB",
        "TABLET",
        "TABLETS",
        "TABS",
        "TOPICAL",
        "VIAL",
        "VIALS",
    }
)
_ARABIC_ATTRIBUTE_TOKENS = frozenset(
    {
        "امبول",
        "امبولات",
        "بخاخ",
        "بخاخة",
        "بخاخات",
        "ج",
        "جل",
        "جيل",
        "جرام",
        "جم",
        "حقن",
        "رذاذ",
        "رشاش",
        "شراب",
        "شريط",
        "شرايط",
        "صابون",
        "قطرة",
        "قطرات",
        "كبسولة",
        "كبسولات",
        "كبسول",
        "كيس",
        "كريم",
        "قرص",
        "اقراص",
        "أقراص",
        "لوشن",
        "مرهم",
        "مل",
        "ملجم",
        "مجم",
        "ميكروجرام",
        "نقط",
        "وحدة",
        "وحدات",
        "فيلم",
        "فيلمس",
        "فيال",
        "فيالات",
        "معلق",
        "معلّق",
    }
)
_SOURCE_PRIORITY = {"tawreed": 2, "egyptian": 1}
_TOKEN_RE = re.compile(r"[A-Z0-9]+")
_ARABIC_TOKEN_RE = re.compile(r"[A-Za-z0-9؀-ۿ]+")
_ARABIC_DIACRITICS_RE = re.compile(r"[ً-ٰٟ]")


@dataclass(frozen=True)
class _BrandSignature:
    canonical: str
    core: str
    modifiers: tuple[str, ...]
    digit_tokens: tuple[str, ...]


@dataclass(frozen=True)
class _IndexedAlias:
    signature: _BrandSignature
    arabic_key: str
    source: str
    deterministic: bool = False


class ExcelTargetAliasResolver:
    """Resolve conservative English aliases to loaded target products.

    ``alias_entries`` may contain :class:`AliasEntry`, mappings with ``en`` /
    ``ar`` / ``source`` keys, or two/three-item tuples. Caller-provided aliases
    whose Arabic side maps to a supplied target product are indexed.
    """

    def __init__(
        self,
        alias_entries: Iterable[AliasEntry | Mapping[str, Any] | Sequence[str]],
        target_products: Iterable[TargetProduct],
        *,
        min_score: float = _DEFAULT_MIN_SCORE,
        min_runner_up_margin: float = _DEFAULT_MIN_MARGIN,
    ) -> None:
        if min_score < _DEFAULT_MIN_SCORE:
            raise ValueError("min_score cannot be lower than the hard floor of 96")
        if min_runner_up_margin < _DEFAULT_MIN_MARGIN:
            raise ValueError("min_runner_up_margin cannot be lower than 4")

        self._min_score = float(min_score)
        self._min_runner_up_margin = float(min_runner_up_margin)
        loaded_products = tuple(target_products)
        targets_by_arabic: dict[str, list[TargetProduct]] = defaultdict(list)
        for product in loaded_products:
            arabic_key = _normalize_arabic_brand(product.name_ar)
            if arabic_key:
                targets_by_arabic[arabic_key].append(product)

        indexed: list[_IndexedAlias] = []
        for raw_entry in _iter_alias_entries(alias_entries):
            entry = _coerce_alias_entry(raw_entry)
            if entry is None:
                continue
            signature = _brand_signature(entry.english)
            arabic_key = _normalize_arabic_brand(entry.arabic)
            if not signature.canonical or not arabic_key:
                continue
            if not targets_by_arabic.get(arabic_key):
                continue
            indexed.append(_IndexedAlias(signature, arabic_key, entry.source))

        # Approved aliases are indexed only when their Arabic identity is a
        # real row in the supplied target catalog.  This is the target scope
        # boundary that prevents either rule from becoming a global alias.
        for entry in APPROVED_ALIAS_ENTRIES:
            signature = _brand_signature(entry.english)
            arabic_key = _normalize_arabic_brand(entry.arabic)
            if signature.canonical and targets_by_arabic.get(arabic_key):
                indexed.append(
                    _IndexedAlias(signature, arabic_key, entry.source, deterministic=True)
                )

        self._aliases = tuple(_deduplicate_aliases(indexed))
        self._targets_by_arabic = {
            key: tuple(products) for key, products in targets_by_arabic.items()
        }

    def resolve(self, item_name: str) -> tuple[AliasCandidate, ...]:
        """Return only hard-floor, high-margin alias evidence.

        The returned candidates are not automatic matches.  Multiple products
        can be returned for one strong alias because target variant uniqueness
        belongs to the integration layer.
        """
        query = _brand_signature(item_name)
        if not query.canonical:
            return ()

        scored: list[tuple[float, _IndexedAlias]] = []
        for alias in self._aliases:
            if alias.deterministic:
                if query.canonical != alias.signature.canonical:
                    continue
                scored.append((100.0, alias))
                continue
            if not _same_meaningful_tokens(query, alias.signature):
                continue
            score = _brand_score(query, alias.signature)
            if score >= self._min_score:
                scored.append((score, alias))
        if not scored:
            return ()

        best_score_by_brand: dict[str, float] = {}
        for score, alias in scored:
            best_score_by_brand[alias.signature.canonical] = max(
                score, best_score_by_brand.get(alias.signature.canonical, 0.0)
            )
        ranked_scores = sorted(best_score_by_brand.values(), reverse=True)
        runner_up_margin = (
            100.0
            if len(ranked_scores) == 1
            else ranked_scores[0] - ranked_scores[1]
        )
        if ranked_scores[0] < self._min_score:
            return ()
        if runner_up_margin < self._min_runner_up_margin:
            return ()

        top_score = ranked_scores[0]
        top_aliases = [
            alias
            for score, alias in scored
            if score == top_score
            and alias.signature.canonical == next(
                brand
                for brand, score_for_brand in best_score_by_brand.items()
                if score_for_brand == top_score
            )
        ]
        candidates_by_product: dict[str, AliasCandidate] = {}
        for alias in sorted(top_aliases, key=_alias_sort_key):
            for product in self._targets_by_arabic.get(alias.arabic_key, ()):
                product_id = product.store_product_id
                candidate = AliasCandidate(
                    product_id=product_id,
                    canonical_brand=alias.signature.canonical,
                    source=alias.source,
                    score=top_score,
                    runner_up_margin=runner_up_margin,
                )
                previous = candidates_by_product.get(product_id)
                if previous is None or _candidate_precedes(candidate, previous):
                    candidates_by_product[product_id] = candidate
        return tuple(candidates_by_product.values())


def _iter_alias_entries(
    entries: Iterable[AliasEntry | Mapping[str, Any] | Sequence[str]] | Mapping[str, Any],
) -> Iterable[AliasEntry | Mapping[str, Any] | Sequence[str]]:
    """Flatten common local dictionary shapes without reading from disk."""
    if not isinstance(entries, Mapping):
        return entries
    if "rows" in entries and isinstance(entries["rows"], Iterable):
        return entries["rows"]
    if "by_en" in entries and isinstance(entries["by_en"], Mapping):
        flattened: list[Mapping[str, Any]] = []
        for english, rows in entries["by_en"].items():
            if not isinstance(rows, Iterable) or isinstance(rows, (str, bytes)):
                continue
            for row in rows:
                if isinstance(row, Mapping):
                    flattened.append({"en": english, **row})
        return flattened
    flattened = []
    for english, rows in entries.items():
        if isinstance(rows, Mapping):
            flattened.append({"en": english, **rows})
        elif isinstance(rows, Iterable) and not isinstance(rows, (str, bytes)):
            for row in rows:
                if isinstance(row, Mapping):
                    flattened.append({"en": english, **row})
    return flattened


def _coerce_alias_entry(
    value: AliasEntry | Mapping[str, Any] | Sequence[str],
) -> AliasEntry | None:
    if isinstance(value, AliasEntry):
        return value
    if isinstance(value, Mapping):
        english = _first_value(value, "en", "english", "name_en", "commercial_name_en")
        arabic = _first_value(value, "ar", "arabic", "name_ar", "commercial_name_ar")
        source = _first_value(value, "source", "evidence", "kind") or "local_alias"
        if not english or not arabic:
            return None
        return AliasEntry(str(english), str(arabic), str(source))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) < 2:
            return None
        source = str(value[2]) if len(value) > 2 else "local_alias"
        return AliasEntry(str(value[0]), str(value[1]), source)
    return None


def _first_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return ""


def _deduplicate_aliases(entries: Iterable[_IndexedAlias]) -> list[_IndexedAlias]:
    seen: set[tuple[str, str, str, bool]] = set()
    result: list[_IndexedAlias] = []
    for entry in entries:
        key = (
            entry.signature.canonical,
            entry.arabic_key,
            entry.source,
            entry.deterministic,
        )
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def _alias_sort_key(alias: _IndexedAlias) -> tuple[int, str, str]:
    return (-_SOURCE_PRIORITY.get(alias.source.casefold(), 0), alias.source, alias.arabic_key)


def _candidate_precedes(candidate: AliasCandidate, previous: AliasCandidate) -> bool:
    candidate_priority = _SOURCE_PRIORITY.get(candidate.source.casefold(), 0)
    previous_priority = _SOURCE_PRIORITY.get(previous.source.casefold(), 0)
    return (candidate_priority, candidate.source) > (previous_priority, previous.source)


def _brand_score(query: _BrandSignature, alias: _BrandSignature) -> float:
    return float(fuzz.token_sort_ratio(query.core, alias.core))


def _same_meaningful_tokens(query: _BrandSignature, alias: _BrandSignature) -> bool:
    return (
        query.modifiers == alias.modifiers
        and query.digit_tokens == alias.digit_tokens
        and len(query.core.split()) == len(alias.core.split())
    )


def _brand_signature(value: str) -> _BrandSignature:
    tokens = _english_tokens(value)
    tokens = _remove_attribute_tokens(tokens)
    modifiers = tuple(token for token in tokens if token in _MEANINGFUL_MODIFIERS)
    digit_tokens = tuple(token for token in tokens if any(char.isdigit() for char in token))
    core_tokens = [token for token in tokens if token not in _MEANINGFUL_MODIFIERS]
    core = " ".join(core_tokens)
    canonical = " ".join(tokens)
    return _BrandSignature(canonical, core, modifiers, digit_tokens)


def _english_tokens(value: str) -> list[str]:
    text = (value or "").upper().replace("µ", "U")
    # Keep dotted IU notation together before punctuation tokenization.
    text = re.sub(r"\bI\s*[.]\s*U\b", "IU", text)
    text = re.sub(r"(?<![A-Z0-9])MGC(?![A-Z0-9])", "MCG", text)
    raw_tokens = _TOKEN_RE.findall(text)
    tokens: list[str] = []
    for raw in raw_tokens:
        match = re.fullmatch(r"(\d+(?:\.\d+)?)([A-Z]+)", raw)
        if match and match.group(2) in _ATTRIBUTE_TOKENS:
            tokens.extend(match.groups())
        else:
            tokens.append(raw)
    return _join_audited_digit_aliases(tokens)


def _join_audited_digit_aliases(tokens: Sequence[str]) -> list[str]:
    """Join only established vitamin-style spellings such as ``B 12``."""
    result: list[str] = []
    index = 0
    while index < len(tokens):
        if (
            tokens[index] in {"B", "D"}
            and index + 1 < len(tokens)
            and tokens[index + 1] in {"3", "6", "12"}
        ):
            result.append(tokens[index] + tokens[index + 1])
            index += 2
            continue
        result.append(tokens[index])
        index += 1
    return result


def _remove_attribute_tokens(tokens: Sequence[str]) -> list[str]:
    result: list[str] = []
    for index, token in enumerate(tokens):
        if token in _ATTRIBUTE_TOKENS:
            continue
        if token.replace(".", "", 1).isdigit() and _near_attribute_token(tokens, index):
            continue
        result.append(token)
    return result


def _near_attribute_token(tokens: Sequence[str], index: int) -> bool:
    return any(
        tokens[other] in _ATTRIBUTE_TOKENS
        for other in range(max(0, index - 1), min(len(tokens), index + 3))
        if other != index
    )


def _normalize_arabic_brand(value: str) -> str:
    text = _ARABIC_DIACRITICS_RE.sub("", (value or "").strip())
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    text = text.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    text = text.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي").replace("ـ", "")
    tokens = _join_audited_arabic_digit_aliases(_ARABIC_TOKEN_RE.findall(text))
    result: list[str] = []
    for index, token in enumerate(tokens):
        folded = token.casefold()
        if folded in _ARABIC_ATTRIBUTE_TOKENS:
            continue
        if folded.isdigit() and _near_arabic_attribute(tokens, index):
            continue
        result.append(folded)
    return " ".join(result)


def _join_audited_arabic_digit_aliases(tokens: Sequence[str]) -> list[str]:
    """Keep Arabic vitamin spellings such as ``بي 12`` intact."""
    result: list[str] = []
    index = 0
    while index < len(tokens):
        if (
            tokens[index] in {"بي", "دي"}
            and index + 1 < len(tokens)
            and tokens[index + 1] in {"3", "6", "12"}
        ):
            result.append(tokens[index] + tokens[index + 1])
            index += 2
            continue
        result.append(tokens[index])
        index += 1
    return result


def _near_arabic_attribute(tokens: Sequence[str], index: int) -> bool:
    return any(
        tokens[other].casefold() in _ARABIC_ATTRIBUTE_TOKENS
        for other in range(max(0, index - 1), min(len(tokens), index + 3))
        if other != index
    )


__all__ = ["AliasCandidate", "AliasEntry", "ExcelTargetAliasResolver"]
