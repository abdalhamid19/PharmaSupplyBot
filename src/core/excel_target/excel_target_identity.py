"""Offline, indexed identity evidence for Arabic Excel supplier catalogs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from src.core.normalization.drug_dictionary import lookup_en
from src.core.normalization.translation import ar_to_en_many_cached_only
from src.core.normalization.tawreed_catalog import load_tawreed_catalog

from .excel_target_loader import TargetProduct


IdentityKind = Literal[
    "native_english",
    "dictionary",
    "cached_translation",
    "tawreed_catalog",
    "manual_review",
    "manual_review_rebound",
]
_ARABIC_DECORATION_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:\u0645\u062c\u0645|\u0645\u0644\u062c\u0645|\u0645\u064a\u0643\u0631\u0648\u062c\u0631\u0627\u0645|\u062c\u0631\u0627\u0645|\u062c\u0645|\u0645\u0644|\u0648\u062d\u062f\u0629|%|"
    r"\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644|\u0634\u0631\u0627\u0628|\u0643\u0631\u064a\u0645|\u062c\u0644|\u062d\u0642\u0646|\u0642\u0637\u0631\u0629|\u0628\u062e\u0627\u062e|\u0643\u064a\u0633)|"
    r"(?:\u0642\u0631\u0635|\u0623\u0642\u0631\u0627\u0635|\u0627\u0642\u0631\u0627\u0635|\u0643\u0628\u0633\u0648\u0644\u0627\u062a|\u0643\u0628\u0633\u0648\u0644\u0629|\u0643\u0628\u0633\u0648\u0644|\u0634\u0631\u0627\u0628|\u0643\u0631\u064a\u0645|\u062c\u0644|\u062c\u064a\u0644|\u062d\u0642\u0646|\u0642\u0637\u0631\u0629|\u0628\u062e\u0627\u062e|\u0633\u0628\u0631\u0627\u0649|\u063a\u0633\u0648\u0644|\u0644\u0644\u0648\u062c\u0647|\u0644\u0644\u0628\u0634\u0631\u0647|\u0644\u0644\u0628\u0634\u0631\u0629|\u0645\u0644\u064a\u0646|\u0645\u0631\u0637\u0628|\u0648\u0645\u0631\u0637\u0628|\u0628\u062f\u064a\u0644|\u0643\u0631\u062a\u0648\u0646|\u062c\u062f\u064a\u062f|\u0643\u064a\u0633)",
    re.IGNORECASE,
)
_ARABIC_METADATA_RE = re.compile(
    r"\d+\s*شريط|\bس\s*(?:ج|ق)\b|\bس\s*جديد\b",
    re.IGNORECASE,
)
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
    by_cached_translation_brand: Mapping[str, tuple[TargetProduct, ...]]
    by_tawreed_brand: Mapping[str, tuple[TargetProduct, ...]]

    @classmethod
    def build(cls, catalog: Sequence[TargetProduct]) -> "ExcelTargetBilingualIndex":
        native: dict[str, list[TargetProduct]] = {}
        arabic: dict[str, list[TargetProduct]] = {}
        for product in catalog:
            if product.trusted_name_en:
                native.setdefault(normalize_english_brand(product.trusted_name_en), []).append(product)
            if product.name_ar:
                arabic.setdefault(normalize_arabic_brand(product.name_ar), []).append(product)
        translations = ar_to_en_many_cached_only([product.name_ar for product in catalog])
        cached: dict[str, list[TargetProduct]] = {}
        for product in catalog:
            translated = translations.get(product.name_ar, "")
            if translated:
                cached.setdefault(normalize_english_brand(translated), []).append(product)
        tawreed: dict[str, list[TargetProduct]] = {}
        target_by_arabic: dict[str, list[TargetProduct]] = {}
        for product in catalog:
            target_by_arabic.setdefault(normalize_arabic_brand(product.name_ar), []).append(product)
        for row in load_tawreed_catalog().get("rows", ()):
            english_brand = normalize_english_brand(row.get("en", ""))
            targets = target_by_arabic.get(normalize_arabic_brand(row.get("ar", "")), ())
            if english_brand:
                tawreed.setdefault(english_brand, []).extend(targets)
        return cls(_freeze(native), _freeze(arabic), _freeze(cached), _freeze(tawreed))

    def identify(self, item_name: str) -> tuple[IdentifiedTarget, ...]:
        brand = normalize_english_brand(item_name)
        found: dict[str, IdentifiedTarget] = {}
        for product in self.by_native_english_brand.get(brand, ()):
            found[product.code] = IdentifiedTarget(
                product, IdentityEvidence("native_english", brand, "native English supplier name", 1.0)
            )
        for alias in lookup_en(brand):
            for product in self.by_arabic_brand.get(normalize_arabic_brand(alias.get("ar", "")), ()):
                found.setdefault(product.code, IdentifiedTarget(
                    product, IdentityEvidence("dictionary", brand, "dictionary direct hit (EN↔AR)", 0.97)
                ))
        for product in self.by_cached_translation_brand.get(brand, ()):
            found.setdefault(product.code, IdentifiedTarget(
                product, IdentityEvidence("cached_translation", brand, "cached translation exact brand", 0.95)
            ))
        for product in self.by_tawreed_brand.get(brand, ()):
            found.setdefault(product.code, IdentifiedTarget(
                product, IdentityEvidence("tawreed_catalog", brand, "Tawreed bilingual catalog alias", 0.94)
            ))
        return tuple(found.values())


def normalize_english_brand(value: str) -> str:
    cleaned = re.sub(r"(?<![A-Za-z])mgc(?![A-Za-z])", "mcg", value or "", flags=re.IGNORECASE)
    cleaned = _EN_DECORATION_RE.sub(" ", cleaned)
    cleaned = re.sub(r"[^A-Za-z]+", " ", cleaned).upper()
    return " ".join(cleaned.split())


def normalize_arabic_brand(value: str) -> str:
    cleaned = _ARABIC_DECORATION_RE.sub(" ", value or "")
    cleaned = _ARABIC_METADATA_RE.sub(" ", cleaned)
    cleaned = re.sub(r"[\u064b-\u065f\u0670]", "", cleaned)
    cleaned = cleaned.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    cleaned = re.sub(r"[^\u0600-\u06ff]+", " ", cleaned)
    normalized = " ".join(cleaned.split())
    return _REVIEWED_ARABIC_SPELLING_VARIANTS.get(normalized, normalized)


def _freeze(mapping: dict[str, list[TargetProduct]]) -> Mapping[str, tuple[TargetProduct, ...]]:
    return {key: tuple(value) for key, value in mapping.items() if key}


__all__ = [
    "ExcelTargetBilingualIndex",
    "IdentifiedTarget",
    "IdentityEvidence",
    "normalize_arabic_brand",
    "normalize_english_brand",
]
