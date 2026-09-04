"""Excel-target product matching engine.

The Excel target source behaves exactly like a Tawreed profile, except
the search surface is an in-memory catalog instead of an HTTP/API/Playwright
session. The matching algorithm is the same pure-Python engine that
already powers the Tawreed flow — :func:`explain_best_product_match` from
:mod:`src.core.matching.product_matching`. We feed it the entire target
catalog as the candidate pool, then honour the saved manual-review
decisions and the same diagnostic emission pipeline used for Tawreed
matches.

When the main engine rejects every candidate on a single-column Arabic
catalog (the typical case for ``البركة شركات.xlsx``-style files), a
secondary bilingual matcher (Cohere translation + karem505 brand
dictionary + form/strength/pack tokens) tries to find a better match.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.core.config.config_models import AppConfig, ExcelTargetConfig, MatchingConfig
from src.core.matching.product_matching import explain_best_product_match
from src.core.matching.product_matching_queries import search_queries_for_item
from src.core.manual_review.manual_review_runtime import (
    filter_manual_review_candidates,
    manual_review_match,
    saved_manual_review_decision,
)
from src.core.matching_types import MatchDecision, SearchMatch
from src.core.normalization.bilingual_brand_matcher import match_brand
from src.core.utils.excel import Item

from .excel_target_loader import (
    TargetProduct,
    iter_target_candidates,
    load_target_catalog_from_excel,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExcelTargetMatch:
    """One Excel-target match result, sharing the Tawreed match shape."""

    target_key: str
    decision: MatchDecision
    catalog_size: int


def load_target_catalog(
    target_path: Path, target_config: ExcelTargetConfig
) -> list[TargetProduct]:
    """Return the parsed catalog for one Excel target, raising on errors."""
    return load_target_catalog_from_excel(target_path, target_config)


def _ar_brand_to_latin(ar_text: str) -> str:
    """Transliterate a short Arabic brand string to Latin for filtering.

    Falls back to the input unchanged when pyarabic is unavailable, so
    the pre-filter degrades gracefully on a missing dependency.
    """
    try:
        import pyarabic.araby as ar
        import pyarabic.trans as pt
    except ImportError:
        return ar_text
    s = ar.strip_tashkeel(ar_text)
    s = ar.strip_tatweel(s)
    s = ar.normalize_ligature(s)
    s = ar.normalize_hamza(s, method="tasheel")
    s = pt.normalize_digits(s, source="all", out="west")
    return pt.convert(s, "arabic", "latin")


def _bilingual_secondary_match(
    item: Item, catalog: list[TargetProduct], min_score: float = 0.7
) -> MatchDecision | None:
    """Fallback matcher: use the bilingual brand matcher against every
    catalog row and accept the best scoring one (>=0.7).

    Two-stage strategy to stay inside Cohere's trial rate limit
    (20 calls/min):
      1. Dictionary check on every row (free, no API calls). Most
         brand-name matches are caught here.
      2. For rows that miss the dictionary, narrow the candidate set
         by form/strength/pack compatibility, then translate only the
         top-50 unique Arabic names through Cohere. Translations are
         cached in-process so subsequent items in the same run reuse
         them.
    """
    from rapidfuzz import fuzz
    from src.core.normalization.bilingual_brand_matcher import (
        _dict_score, _compatibility_factor, _brand_only, _translation_score,
    )

    item_name = item.name
    en_brand = _brand_only(item_name).upper()

    best: tuple[float, TargetProduct, str, str] | None = None
    seen_translations: dict[str, str] = {}

    # Pre-compute transliterated Arabic brands once (cheap) so we can
    # filter to candidates that share at least one Latin character
    # with the English brand before spending a Cohere call.
    candidates: list[tuple[float, TargetProduct, str]] = []
    for product in catalog:
        if not product.name:
            continue
        dict_score, reason, _, manufacturer = _dict_score(item_name, product.name)
        if dict_score > 0.0:
            # Dictionary direct hit (>=0.95) is a strong signal even if
            # strength/pack tokens differ; don't penalize it.
            if dict_score >= 0.95:
                if best is None or dict_score > best[0]:
                    best = (dict_score, product, reason, manufacturer)
            else:
                score = dict_score * _compatibility_factor(item_name, product.name)
                if best is None or score > best[0]:
                    best = (score, product, reason, manufacturer)
            continue
        ar_brand = _brand_only(product.name)
        if not ar_brand:
            continue
        # Cheap pre-filter: transliterate the Arabic brand to Latin and
        # then check character overlap with the English brand.
        ar_brand_latin = _ar_brand_to_latin(ar_brand)
        if ar_brand_latin:
            shared = set(en_brand.lower()) & set(ar_brand_latin.lower())
            if len(shared) < 2:
                continue
        quick = fuzz.token_set_ratio(en_brand, (ar_brand_latin or ar_brand).upper()) / 100.0
        if quick < 0.3:
            continue
        candidates.append((quick, product, manufacturer))

    if not candidates or best is not None and best[0] >= min_score:
        return _finalize_fallback(best, item_name, min_score)

    candidates.sort(key=lambda x: x[0], reverse=True)
    candidates = candidates[:30]

    from src.core.normalization.translation import ar_to_en
    for _, product, manufacturer in candidates:
        if product.name in seen_translations:
            translated = seen_translations[product.name]
        else:
            translated = ar_to_en(product.name)
            seen_translations[product.name] = translated
        if not translated or translated == product.name:
            continue
        score = _translation_score(item_name, translated, en_brand)
        score *= _compatibility_factor(item_name, product.name)
        if score >= min_score and (best is None or score > best[0]):
            best = (score, product, f"translation similarity ({score:.2f})", manufacturer)

    return _finalize_fallback(best, item_name, min_score)


def _finalize_fallback(
    best: tuple[float, TargetProduct, str, str] | None,
    item_name: str,
    min_score: float = 0.7,
) -> MatchDecision | None:
    if best is None or best[0] < min_score:
        return None
    score, product, reason, _manufacturer = best
    best_match = SearchMatch(
        query=item_name,
        row_index=0,
        score=score * 100,
        data={
            "productNameEn": product.name,
            "productNameEnFallback": product.name,
            "productName": product.name,
            "availableQuantity": 1,
            "productsCount": 1,
            "discountPercent": product.discount_percent or 0,
            "storeProductId": product.code or "",
            "excelTarget": True,
            "excelTargetSourceFile": product.source_file,
            "excelTargetRaw": {
                "name": product.name,
                "price": product.price,
                "discount": product.discount_percent,
                "code": product.code,
            },
            "priceMeaning": product.price_meaning or "public_with_discount",
            "price": product.price,
        },
    )
    logger.info(
        "bilingual fallback accepted %s for item %s: %s (score=%.2f)",
        product.name,
        item_name,
        reason,
        score,
    )
    return MatchDecision(
        best_match=best_match,
        diagnostics=[],
        final_reason=f"bilingual fallback: {reason}",
    )


def find_best_match_in_target(
    item: Item,
    target_key: str,
    catalog: list[TargetProduct],
    matching_config: MatchingConfig,
) -> ExcelTargetMatch | None:
    """Run the matching engine against one Excel target catalog.

    Returns ``None`` when the catalog is empty. The returned
    :class:`ExcelTargetMatch` always carries a :class:`MatchDecision`,
    even when no candidate is accepted, so callers can persist the
    diagnostic and the rejection reason.
    """
    if not catalog:
        return MatchDecision(
            best_match=None,
            diagnostics=[],
            final_reason="Excel target catalog is empty.",
        ) and _empty_match(target_key)

    candidates = iter_target_candidates(catalog)
    queries = search_queries_for_item(item)
    review_decision = saved_manual_review_decision(item)
    forced = manual_review_match(item, [(q, candidates) for q in queries], review_decision)
    if forced:
        return ExcelTargetMatch(
            target_key=target_key,
            decision=forced,
            catalog_size=len(catalog),
        )

    filtered = filter_manual_review_candidates(
        item,
        [(q, candidates) for q in queries],
        review_decision,
    )
    decision = explain_best_product_match(item, filtered, matching_config)
    needs_fallback = (
        decision.best_match is None or "Ambiguous" in decision.final_reason
    ) and getattr(matching_config, "enable_bilingual_secondary_match", False)
    if needs_fallback:
        fallback = _bilingual_secondary_match(
            item, catalog, min_score=getattr(matching_config, "bilingual_min_score", 0.7)
        )
        if fallback is not None:
            decision = fallback
    return ExcelTargetMatch(
        target_key=target_key,
        decision=decision,
        catalog_size=len(catalog),
    )


def match_item_against_all_targets(
    item: Item,
    app_config: AppConfig,
    catalogs: dict[str, list[TargetProduct]],
) -> dict[str, ExcelTargetMatch | None]:
    """Run one item against every supplied Excel target catalog."""
    matching_config = app_config.matching
    results: dict[str, ExcelTargetMatch | None] = {}
    for target_key, catalog in catalogs.items():
        results[target_key] = find_best_match_in_target(
            item, target_key, catalog, matching_config
        )
    return results


def _empty_match(target_key: str) -> ExcelTargetMatch:
    """Return an empty :class:`ExcelTargetMatch` for the catalog."""
    return ExcelTargetMatch(
        target_key=target_key,
        decision=MatchDecision(
            best_match=None,
            diagnostics=[],
            final_reason="Excel target catalog is empty.",
        ),
        catalog_size=0,
    )


def first_accepted_match(
    matches: dict[str, ExcelTargetMatch | None],
) -> tuple[str, ExcelTargetMatch] | None:
    """Return the first accepted match across all Excel targets."""
    for target_key, match in matches.items():
        if match is None:
            continue
        if match.decision.best_match is not None:
            return target_key, match
    return None


__all__ = [
    "ExcelTargetMatch",
    "load_target_catalog",
    "find_best_match_in_target",
    "match_item_against_all_targets",
    "first_accepted_match",
]