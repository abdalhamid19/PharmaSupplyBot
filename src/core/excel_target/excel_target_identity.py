"""Offline, indexed identity evidence for Arabic Excel supplier catalogs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from src.core.normalization.drug_dictionary import load_dictionary, lookup_en
from src.core.normalization.translation import (
    ar_to_en_many,
    ar_to_en_many_cached_only,
)
from src.core.normalization.tawreed_catalog import load_tawreed_catalog

from .excel_target_aliases import AliasEntry, ExcelTargetAliasResolver
from .excel_target_loader import TargetProduct


IdentityKind = Literal[
    "native_english",
    "dictionary",
    "cached_translation",
    "cohere_translation",
    "safe_alias",
    "tawreed_catalog",
    "manual_review",
    "manual_review_rebound",
    "review_identity",
    "review_identity_prefix",
]
_ARABIC_DECORATION_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:\u0645\u062c\u0645|\u0645\u0644\u062c\u0645|\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645|\u062c\u0631\u0627\u0645|\u062c\u0645|\u0645\u0644\u0644\u0649|\u0645\u0644|\u0648\u062d\u062f\u0629|%|"
    r"\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644|\u0627\u0645\u0628\u0648\u0644\u0627\u062a|\u0627\u0645\u0628\u0648\u0644|\u0634\u0631\u0627\u0628|\u0643\u0631\u064a\u0645|\u062c\u0644|\u062d\u0642\u0646|\u0642\u0637\u0631\u0629|\u0628\u062e\u0627\u062e|\u0643\u064a\u0633)|"
    r"(?:\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644|\u0627\u0645\u0628\u0648\u0644\u0627\u062a|\u0627\u0645\u0628\u0648\u0644|\u0634\u0631\u0627\u0628|\u0643\u0631\u064a\u0645|\u062c\u0644|\u062c\u064a\u0644|\u062d\u0642\u0646|\u0646\u0642\u0637|\u0642\u0637\u0631\u0629|\u0642\u0637\u0631\u0647|\u0628\u0627\u0644\u0641\u0645|\u0627\u0644\u0641\u0645|\u0645\u0644\u064a\u0646|\u0628\u062e\u0627\u062e\s+\u0645\u0648\u0636\u0639\u064a|\u0628\u062e\u0627\u062e|\u0633\u0628\u0631\u0627\u0649|\u063a\u0633\u0648\u0644|\u0644\u0644\u0648\u062c\u0647|\u0644\u0644\u0628\u0634\u0631\u0647|\u0644\u0644\u0628\u0634\u0631\u0629|\u0645\u0631\u0637\u0628|\u0648\u0645\u0631\u0637\u0628|\u0628\u062f\u064a\u0644|\u0643\u0631\u062a\u0648\u0646|\u062c\u062f\u064a\u062f|\u0643\u064a\u0633)",
    re.IGNORECASE,
)
_ARABIC_METADATA_RE = re.compile(
    r"\d+\s*شريط|\bس\s*(?:ج|ق)\b|\bس\s*جديد\b",
    re.IGNORECASE,
)
_ARABIC_REVIEW_DECORATION_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:مجم|ملجم|ميكروجرام|جرام|جم|مل|وحدة|%|"
    r"مبول|مبولة|مبولات|امبول|امبولة|امبولات|قرص|اقراص|أقراص|"
    r"كبسول|كبسولة|كبسولات|شريط|شراب|كريم|جل|جيل|حقن|قطرة|قطرات|"
    r"بخاخ|سبراي|ساشيه|كيس)|"
    r"(?:مبول|مبولة|مبولات|امبول|امبولة|امبولات|قرص|اقراص|أقراص|"
    r"كبسول|كبسولة|كبسولات|شريط|شراب|كريم|جل|جيل|حقن|قطرة|قطرات|"
    r"بخاخ|سبراي|ساشيه|كيس)",
    re.IGNORECASE,
)
_ARABIC_REVIEW_STATUS_RE = re.compile(
    r"\s+(?:س(?:\s+(?:ج|جديد))?|جديد|قديم)\b", re.IGNORECASE
)
_ARABIC_LEGACY_STATUS_RE = re.compile(r"\s+\u0642\u062f\u064a\u0645\s*$")
_ARABIC_ATOR_PREFIX_RE = re.compile(r"^\s*\u0627\u062a\u0648\u0631(?:\s|$)")
_ARABIC_ATOR_SUFFIX_RE = re.compile(r"\s+\u0633\s*$")
_ARABIC_SLASH_UNIT_RE = re.compile(r"(?<=/)\s*\u0645\u0644(?=\s|$)")
_REVIEWED_ARABIC_SPELLING_VARIANTS = {
    "اجريكس": "اجركس",
    "الفينترن": "الفنترن",
    "ازماكاست": "ازماكست",
}
_EN_DECORATION_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mcg|mgc|ug|mg|gm|g|ml|iu|%|tab|tabs|tablet|tablets|"
    r"cap|caps|capsule|capsules|film|flim|films|flims|supp|suppository|suppositories|"
    r"syrup|cream|gel|inj|injection|drops|spray|sachet|amp|ampoule|ampoules|"
    r"milk|susp|suspension|aerosol|powder|pre|filled|syringe|im)\b|"
    r"\b(?:mcg|mgc|ug|mg|gm|g|ml|iu|tab|tabs|tablet|tablets|cap|caps|capsule|"
    r"capsules|film|flim|films|flims|supp|suppository|suppositories|syrup|cream|"
    r"gel|inj|injection|drops|spray|sachet|amp|ampoule|ampoules|milk|susp|"
    r"suspension|aerosol|powder|pre|filled|syringe|im|oral|topical|ointment|oint|f|c)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class IdentityEvidence:
    kind: IdentityKind
    canonical_brand: str
    detail: str
    confidence: float


@dataclass(frozen=True)
class IdentifiedTarget:
    product: TargetProduct
    evidence: IdentityEvidence


@dataclass(frozen=True)
class ExcelTargetBilingualIndex:
    """Catalog indices built once; no Tawreed network/API query is permitted.

    The local ``tawreed_products.csv`` file may provide an alias during index
    construction, but it never contributes a Baraka candidate, price, or
    availability record.
    """

    by_native_english_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_arabic_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_dictionary_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_cached_translation_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_cached_cohere_translation_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_cohere_translation_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_tawreed_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_review_english_brand: Mapping[
        str, tuple[tuple[TargetProduct, bool], ...]
    ]
    alias_resolver: ExcelTargetAliasResolver
    alias_products_by_id: Mapping[str, tuple[TargetProduct, ...]]
    review_aliases: tuple[AliasEntry, ...] = ()

    @classmethod
    def build(
        cls,
        catalog: Sequence[TargetProduct],
        *,
        allow_live_translation: bool = False,
    ) -> "ExcelTargetBilingualIndex":
        native: dict[str, list[TargetProduct]] = {}
        arabic: dict[str, list[TargetProduct]] = {}
        for product in catalog:
            if product.trusted_name_en:
                native.setdefault(normalize_english_brand(product.trusted_name_en), []).append(product)
            if product.name_ar:
                arabic.setdefault(normalize_arabic_brand(product.name_ar), []).append(product)
        tawreed: dict[str, list[TargetProduct]] = {}
        dictionary: dict[str, list[TargetProduct]] = {}
        target_by_arabic: dict[str, list[TargetProduct]] = {}
        review_target_by_root: dict[str, list[tuple[str, TargetProduct]]] = {}
        tawreed_arabic_names: set[str] = set()
        dictionary_arabic_names: set[str] = set()
        for product in catalog:
            arabic_brand = normalize_arabic_brand(product.name_ar)
            if arabic_brand:
                target_by_arabic.setdefault(arabic_brand, []).append(product)
            review_brand = normalize_arabic_review_brand(product.name_ar)
            if review_brand:
                review_root = review_brand.split(" ", 1)[0]
                review_target_by_root.setdefault(review_root, []).append(
                    (review_brand, product)
                )
        tawreed_rows = tuple(load_tawreed_catalog().get("rows", ()))
        alias_entries: list[AliasEntry] = []
        review_aliases: list[tuple[str, str]] = []
        review_alias_entries: list[AliasEntry] = []
        for row in tawreed_rows:
            english_brand = normalize_english_brand(row.get("en", ""))
            arabic_brand = normalize_arabic_brand(row.get("ar", ""))
            if not arabic_brand:
                continue
            targets = target_by_arabic.get(arabic_brand, ())
            review_targets = _review_targets_for_alias(
                review_target_by_root, arabic_brand
            )
            if english_brand:
                tawreed.setdefault(english_brand, []).extend(targets)
                if targets or review_targets:
                    if targets:
                        alias_entries.append(
                            AliasEntry(row.get("en", ""), row.get("ar", ""), "tawreed")
                        )
                    if review_targets:
                        review_aliases.append((english_brand, arabic_brand))
                        review_alias_entries.append(
                            AliasEntry(row.get("en", ""), row.get("ar", ""), "tawreed")
                        )
                if targets:
                    tawreed_arabic_names.add(arabic_brand)

        dictionary_rows = load_dictionary().get("by_en", {})
        for english_name, rows in dictionary_rows.items():
            english_brand = normalize_english_brand(english_name)
            if not english_brand:
                continue
            for row in rows:
                arabic_brand = normalize_arabic_brand(row.get("ar", ""))
                if not arabic_brand:
                    continue
                targets = target_by_arabic.get(arabic_brand, ())
                review_targets = _review_targets_for_alias(
                    review_target_by_root, arabic_brand
                )
                if targets:
                    dictionary.setdefault(english_brand, []).extend(targets)
                    dictionary_arabic_names.add(arabic_brand)
                    alias_entries.append(
                        AliasEntry(english_name, row.get("ar", ""), "egyptian")
                    )
                if review_targets:
                    review_aliases.append((english_brand, arabic_brand))
                    review_alias_entries.append(
                        AliasEntry(english_name, row.get("ar", ""), "egyptian")
                    )

        review: dict[str, list[tuple[TargetProduct, bool]]] = {}
        for english_brand, arabic_brand in review_aliases:
            for product, is_prefix in _review_targets_for_alias(
                review_target_by_root, arabic_brand
            ):
                review.setdefault(english_brand, []).append((product, is_prefix))

        names = [product.name_ar for product in catalog if product.name_ar]
        cached_translations = ar_to_en_many_cached_only(names)
        cached: dict[str, list[TargetProduct]] = {}
        cached_cohere: dict[str, list[TargetProduct]] = {}
        cached_models = getattr(cached_translations, "models", {})
        for product in catalog:
            translated = _translation_for_name(cached_translations, product.name_ar)
            if translated:
                destination = (
                    cached_cohere
                    if str(cached_models.get(product.name_ar, "")).startswith("command-")
                    else cached
                )
                destination.setdefault(normalize_english_brand(translated), []).append(product)

        live: dict[str, list[TargetProduct]] = {}
        if allow_live_translation:
            cached_names = set(cached_translations)
            unresolved = list(
                dict.fromkeys(
                    name
                    for name in names
                    if name not in cached_names
                    and normalize_arabic_brand(name) not in tawreed_arabic_names
                    and normalize_arabic_brand(name) not in dictionary_arabic_names
                )
            )
            live_translations = ar_to_en_many(unresolved) if unresolved else {}
            for product in catalog:
                translated = _translation_for_name(live_translations, product.name_ar)
                if translated:
                    live.setdefault(normalize_english_brand(translated), []).append(product)

        alias_products: dict[str, list[TargetProduct]] = {}
        for product in catalog:
            alias_products.setdefault(product.store_product_id, []).append(product)

        return cls(
            _freeze(native),
            _freeze(arabic),
            _freeze(dictionary),
            _freeze(cached),
            _freeze(cached_cohere),
            _freeze(live),
            _freeze(tawreed),
            _freeze_review(review),
            ExcelTargetAliasResolver(alias_entries, catalog),
            _freeze(alias_products),
            tuple(review_alias_entries),
        )

    def identify(self, item_name: str) -> tuple[IdentifiedTarget, ...]:
        brand = normalize_english_brand(item_name)
        found: dict[tuple[str, str, int, str], IdentifiedTarget] = {}
        for product in self.by_native_english_brand.get(brand, ()):
            found[_target_identity_key(product)] = IdentifiedTarget(
                product, IdentityEvidence("native_english", brand, "native English supplier name", 1.0)
            )
        for product in self.by_tawreed_brand.get(brand, ()):
            found.setdefault(_target_identity_key(product), IdentifiedTarget(
                product, IdentityEvidence("tawreed_catalog", brand, "Tawreed bilingual catalog alias", 0.94)
            ))
        for product in self.by_dictionary_brand.get(brand, ()):
            found.setdefault(_target_identity_key(product), IdentifiedTarget(
                product, IdentityEvidence("dictionary", brand, "dictionary direct hit (EN↔AR)", 0.97)
            ))
        for alias in lookup_en(brand):
            for product in self.by_arabic_brand.get(normalize_arabic_brand(alias.get("ar", "")), ()):
                found.setdefault(_target_identity_key(product), IdentifiedTarget(
                    product, IdentityEvidence("dictionary", brand, "dictionary direct hit (EN↔AR)", 0.97)
                ))
        for alias in self.alias_resolver.resolve(item_name):
            for product in self.alias_products_by_id.get(alias.product_id, ()):
                found.setdefault(_target_identity_key(product), IdentifiedTarget(
                    product,
                    IdentityEvidence(
                        "safe_alias",
                        alias.canonical_brand,
                        f"{alias.source} audited alias ({alias.score:.1f}, margin {alias.runner_up_margin:.1f})",
                        alias.score / 100.0,
                    ),
                ))
        for product in self.by_cached_translation_brand.get(brand, ()):
            found.setdefault(_target_identity_key(product), IdentifiedTarget(
                product, IdentityEvidence("cached_translation", brand, "cached translation exact brand", 0.95)
            ))
        for product in self.by_cached_cohere_translation_brand.get(brand, ()):
            found.setdefault(_target_identity_key(product), IdentifiedTarget(
                product,
                IdentityEvidence(
                    "cohere_translation",
                    brand,
                    "cached Cohere translation exact brand",
                    0.90,
                ),
            ))
        for product in self.by_cohere_translation_brand.get(brand, ()):
            found.setdefault(_target_identity_key(product), IdentifiedTarget(
                product, IdentityEvidence("cohere_translation", brand, "Cohere translation exact brand", 0.90)
            ))
        return tuple(found.values())

    def identify_review_candidates(self, item_name: str) -> tuple[IdentifiedTarget, ...]:
        """Return review-only rows anchored by audited bilingual identity."""
        brand = normalize_english_brand(item_name)
        found: dict[tuple[str, str, int, str], IdentifiedTarget] = {}
        for product, is_prefix in self.by_review_english_brand.get(brand, ()):
            evidence_kind = (
                "review_identity_prefix" if is_prefix else "review_identity"
            )
            found[_target_identity_key(product)] = IdentifiedTarget(
                product,
                IdentityEvidence(
                    evidence_kind,
                    brand,
                    (
                        "review-only anchored Arabic prefix expansion"
                        if is_prefix
                        else "review-only anchored Arabic brand expansion"
                    ),
                    0.82 if is_prefix else 0.90,
                ),
            )
        return tuple(found.values())


def _target_identity_key(product: TargetProduct) -> tuple[str, str, int, str]:
    return (
        product.store_product_id,
        product.source_file,
        product.source_row_number,
        product.name,
    )


def _review_targets_for_alias(
    review_target_by_root: Mapping[str, list[tuple[str, TargetProduct]]],
    arabic_brand: str,
) -> tuple[tuple[TargetProduct, bool], ...]:
    """Return target rows anchored by a review-only Arabic alias."""
    review_brand = normalize_arabic_review_brand(arabic_brand)
    if not review_brand:
        return ()
    review_root = review_brand.split(" ", 1)[0]
    return tuple(
        (product, target_brand != review_brand)
        for target_brand, product in review_target_by_root.get(review_root, ())
        if target_brand == review_brand
        or target_brand.startswith(f"{review_brand} ")
    )


def normalize_english_brand(value: str) -> str:
    cleaned = re.sub(r"(?<![A-Za-z])mgc(?![A-Za-z])", "mcg", value or "", flags=re.IGNORECASE)
    cleaned = _EN_DECORATION_RE.sub(" ", cleaned)
    tokens = re.findall(r"[A-Za-z]+[0-9]+|[0-9]+[A-Za-z]+|[A-Za-z]+", cleaned)
    return " ".join(token.upper() for token in tokens)


def _strip_narrow_arabic_catalog_status(value: str) -> str:
    """Drop only audited catalog suffixes when a variant is also present.

    ``قديم`` is a status marker only in the approved REGCOR-style shape, and
    the one-letter ``س`` suffix is scoped to the Arabic ATOR brand. Requiring
    a preceding dosage/form token keeps either word available as brand text
    in an otherwise unqualified name.
    """
    value = _ARABIC_SLASH_UNIT_RE.sub(" ", value)
    has_catalog_attributes = _ARABIC_DECORATION_RE.search(value) is not None
    if not has_catalog_attributes:
        return value
    cleaned = _ARABIC_LEGACY_STATUS_RE.sub("", value)
    if _ARABIC_ATOR_PREFIX_RE.match(cleaned):
        cleaned = _ARABIC_ATOR_SUFFIX_RE.sub("", cleaned)
    return cleaned


def normalize_arabic_brand(value: str) -> str:
    cleaned = (value or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    cleaned = _strip_narrow_arabic_catalog_status(cleaned)
    cleaned = _ARABIC_DECORATION_RE.sub(" ", cleaned)
    cleaned = _ARABIC_METADATA_RE.sub(" ", cleaned)
    cleaned = re.sub(r"[\u064b-\u065f\u0670]", "", cleaned)
    cleaned = cleaned.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    cleaned = re.sub(r"[^\u0600-\u06ff0-9]+", " ", cleaned)
    normalized = " ".join(token for token in cleaned.split() if not token.isdigit())
    return _REVIEWED_ARABIC_SPELLING_VARIANTS.get(normalized, normalized)


def normalize_arabic_review_brand(value: str) -> str:
    """Normalize Arabic catalog variants for manual-review recall only."""
    text = (value or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    has_decoration = bool(_ARABIC_REVIEW_DECORATION_RE.search(text))
    if has_decoration:
        text = _ARABIC_REVIEW_STATUS_RE.sub(" ", text)
    text = _ARABIC_REVIEW_DECORATION_RE.sub(" ", text)
    return normalize_arabic_brand(text)


def _freeze(mapping: dict[str, list[TargetProduct]]) -> Mapping[str, tuple[TargetProduct, ...]]:
    return {key: tuple(value) for key, value in mapping.items() if key}


def _freeze_review(
    mapping: dict[str, list[tuple[TargetProduct, bool]]],
) -> Mapping[str, tuple[tuple[TargetProduct, bool], ...]]:
    return {key: tuple(value) for key, value in mapping.items() if key}


def _translation_for_name(translations: Mapping[str, str], name: str) -> str:
    """Read either the original or whitespace-cleaned translation key."""
    cleaned = re.sub(r"\s+", " ", name or "").strip()
    return translations.get(name, "") or translations.get(cleaned, "")


__all__ = [
    "ExcelTargetBilingualIndex",
    "IdentifiedTarget",
    "IdentityEvidence",
    "normalize_arabic_brand",
    "normalize_arabic_review_brand",
    "normalize_english_brand",
]
