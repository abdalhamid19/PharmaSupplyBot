"""Excel-target product matching engine.

The Excel target source behaves exactly like a Tawreed profile, except
the search surface is an in-memory catalog instead of an HTTP/API/Playwright
session. The matching algorithm is the same pure-Python engine that
already powers the Tawreed flow — :func:`explain_best_product_match` from
:mod:`src.core.matching.product_matching`. We feed it the entire target
catalog as the candidate pool, then honour the saved manual-review
decisions and the same diagnostic emission pipeline used for Tawreed
matches.
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