"""Safe, offline matching for supplier Excel catalogs.

Arabic rows are never treated as English text. A row is accepted only after
offline identity evidence and strict variant compatibility have both passed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from src.core.config.config_models import AppConfig, ExcelTargetConfig, MatchingConfig
from src.core.matching.product_matching import explain_best_product_match
from src.core.matching.product_matching_queries import search_queries_for_item
from src.core.matching_types import MatchDecision, SearchMatch
from src.core.matching.candidate_identity import candidate_store_product_id
from src.core.manual_review.manual_review_runtime import saved_manual_review_decision
from src.core.utils.excel import Item

from .excel_target_identity import ExcelTargetBilingualIndex, IdentifiedTarget, IdentityEvidence
from .excel_target_loader import TargetProduct, load_target_catalog_from_excel
from .product_attributes import CompatibilityResult, validate_product_compatibility
from .excel_target_review_candidates import (
    ExcelTargetReviewCandidate,
    build_review_candidates,
)


@dataclass(frozen=True)
class ExcelTargetMatch:
    """One Excel-target match result, sharing the Tawreed match shape."""

    target_key: str
    decision: MatchDecision
    catalog_size: int
    review_candidates: tuple[ExcelTargetReviewCandidate, ...] = ()


class ExcelTargetMatcher:
    """Reusable, offline matcher for one loaded target catalog."""

    def __init__(self, target_key: str, catalog: Sequence[TargetProduct]) -> None:
        self.target_key = target_key
        self.catalog = tuple(catalog)
        self.identity_index = ExcelTargetBilingualIndex.build(self.catalog)

    def match(self, item: Item, config: MatchingConfig) -> ExcelTargetMatch:
        started = time.perf_counter()
        if not self.catalog:
            return _empty_match(self.target_key)

        manual = _scoped_manual_review(item, self.target_key, self.catalog)
        if manual is not None:
            return ExcelTargetMatch(self.target_key, manual, len(self.catalog))
        identified = self.identity_index.identify(item.name)
        accepted, rejected = _compatible_identified(item, identified)
        if len(accepted) == 1:
            decision = _identity_decision(item, accepted[0][0], started)
        elif len(accepted) > 1:
            decision = MatchDecision(None, [], "Ambiguous verified Excel-target candidates")
        else:
            decision = _native_english_decision(item, self.catalog, config)
            if decision.best_match is None:
                reason = rejected[0] if rejected else "Arabic-only candidate lacks verified brand identity"
                decision = MatchDecision(None, decision.diagnostics, reason)
        review_candidates = build_review_candidates(
            item,
            self.target_key,
            self.catalog,
            identified=identified,
            diagnostics=decision.diagnostics,
        )
        return ExcelTargetMatch(
            self.target_key,
            decision,
            len(self.catalog),
            review_candidates,
        )


def load_target_catalog(target_path: Path, target_config: ExcelTargetConfig) -> list[TargetProduct]:
    """Return the parsed catalog for one Excel target, raising on errors."""
    return load_target_catalog_from_excel(target_path, target_config)


def find_best_match_in_target(
    item: Item,
    target_key: str,
    catalog: list[TargetProduct],
    matching_config: MatchingConfig,
) -> ExcelTargetMatch:
    """Compatibility wrapper; batch callers must reuse :class:`ExcelTargetMatcher`."""
    return ExcelTargetMatcher(target_key, catalog).match(item, matching_config)


def match_item_against_all_targets(
    item: Item,
    app_config: AppConfig,
    catalogs: dict[str, list[TargetProduct]],
) -> dict[str, ExcelTargetMatch]:
    return {
        target_key: ExcelTargetMatcher(target_key, catalog).match(item, app_config.matching)
        for target_key, catalog in catalogs.items()
    }


def first_accepted_match(
    matches: dict[str, ExcelTargetMatch | None],
) -> tuple[str, ExcelTargetMatch] | None:
    for target_key, match in matches.items():
        if match is not None and match.decision.best_match is not None:
            return target_key, match
    return None


def _compatible_identified(
    item: Item, identified: Sequence[IdentifiedTarget]
) -> tuple[list[tuple[IdentifiedTarget, CompatibilityResult]], list[str]]:
    accepted: list[tuple[IdentifiedTarget, CompatibilityResult]] = []
    rejected: list[str] = []
    for candidate in identified:
        compatibility = validate_product_compatibility(item.name, candidate.product.name_ar)
        if compatibility.accepted:
            accepted.append((candidate, compatibility))
        else:
            rejected.append(compatibility.rejection_reason)
    return accepted, rejected


def _scoped_manual_review(
    item: Item, target_key: str, catalog: Sequence[TargetProduct]
) -> MatchDecision | None:
    """Use only a review explicitly bound to this Excel target and row."""
    decision = saved_manual_review_decision(
        item,
        matching_source="excel-target",
        excel_target_key=target_key,
        include_legacy=False,
    )
    if not decision or not decision.approved or decision.excel_target_key != target_key:
        return None
    for product in catalog:
        product_id = candidate_store_product_id(product.to_candidate_dict())
        if product.code != decision.correct_store_product_id and product_id != decision.correct_store_product_id:
            continue
        if (
            decision.excel_target_source_file
            and product.source_file != decision.excel_target_source_file
        ):
            continue
        identified = IdentifiedTarget(
            product,
            IdentityEvidence("manual_review", "", "scoped saved manual review", 1.0),
        )
        return _identity_decision(item, identified, time.perf_counter())
    return None


def _identity_decision(item: Item, identified: IdentifiedTarget, started: float) -> MatchDecision:
    product = identified.product
    evidence = identified.evidence
    data = product.to_candidate_dict()
    data.update(
        {
            "verified_brand_identity": True,
            "identity_evidence_kind": evidence.kind,
            "identity_evidence": evidence.detail,
            "compatibility_status": "compatible",
            "compatibility_rejection": "",
            "match_elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    )
    return MatchDecision(
        SearchMatch(item.name, 0, evidence.confidence * 20, data),
        [],
        f"Excel-target verified {evidence.kind}: {evidence.detail}",
    )


def _native_english_decision(
    item: Item, catalog: Sequence[TargetProduct], config: MatchingConfig
) -> MatchDecision:
    """Use the established threshold contract only for genuine English rows."""
    candidates = [product.to_candidate_dict() for product in catalog if product.trusted_name_en]
    if not candidates:
        return MatchDecision(None, [], "Arabic-only candidate lacks verified brand identity")
    queries = search_queries_for_item(item)
    decision = explain_best_product_match(item, [(query, candidates) for query in queries], config)
    if decision.best_match is None:
        return decision
    compatibility = validate_product_compatibility(
        item.name, str(decision.best_match.data.get("productName", ""))
    )
    if not compatibility.accepted:
        return MatchDecision(None, decision.diagnostics, compatibility.rejection_reason)
    return decision


def _empty_match(target_key: str) -> ExcelTargetMatch:
    return ExcelTargetMatch(
        target_key,
        MatchDecision(None, [], "Excel target catalog is empty."),
        0,
    )


__all__ = [
    "ExcelTargetMatch",
    "ExcelTargetMatcher",
    "ExcelTargetReviewCandidate",
    "build_review_candidates",
    "find_best_match_in_target",
    "first_accepted_match",
    "load_target_catalog",
    "match_item_against_all_targets",
]
