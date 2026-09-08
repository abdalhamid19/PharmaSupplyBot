"""Safe, offline matching for supplier Excel catalogs.

Arabic rows are never treated as English text. A row is accepted only after
offline identity evidence and strict variant compatibility have both passed.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

from src.core.config.config_models import AppConfig, ExcelTargetConfig, MatchingConfig
from src.core.matching.product_matching import explain_best_product_match
from src.core.matching.product_matching_queries import search_queries_for_item
from src.core.matching_types import DecisionSource, MatchDecision, SearchMatch
from src.core.matching.candidate_identity import candidate_store_product_id
from src.core.manual_review.manual_review_runtime import saved_manual_review_decision
from src.core.manual_review.manual_review_store import ManualReviewStore
from src.core.utils.excel import Item

from .excel_target_identity import (
    ExcelTargetBilingualIndex,
    IdentifiedTarget,
    IdentityEvidence,
    normalize_arabic_brand,
    normalize_english_brand,
)
from .excel_target_loader import TargetProduct, load_target_catalog_from_excel
from .product_attributes import CompatibilityResult, validate_product_compatibility
from .excel_target_review_candidates import (
    ExcelTargetReviewCandidate,
    build_review_candidates,
)

logger = logging.getLogger(__name__)


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
        self._catalog_by_id = {
            product.store_product_id: product for product in self.catalog
        }
        self._native_english_candidate_templates = tuple(
            product.to_candidate_dict()
            for product in self.catalog
            if product.trusted_name_en
        )

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
            decision = _native_english_decision(
                item, self._native_english_candidate_templates, config
            )
            if decision.best_match is None:
                reason = rejected[0] if rejected else "Arabic-only candidate lacks verified brand identity"
                decision = MatchDecision(None, decision.diagnostics, reason)
        review_candidates = build_review_candidates(
            item,
            self.target_key,
            self.catalog,
            identified=identified,
            diagnostics=decision.diagnostics,
            catalog_by_id=self._catalog_by_id,
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
    if not decision or decision.excel_target_key != target_key:
        return None
    if decision.manual_decision in {"needs_correction", "not_matching"}:
        return MatchDecision(None, [], f"Saved {decision.manual_decision} requires manual review")
    if not decision.approved:
        return MatchDecision(None, [], "Saved decision is not approved")

    compatible: list[TargetProduct] = []
    rejected: list[str] = []
    saved_en = normalize_english_brand(decision.correct_product_name)
    saved_ar = normalize_arabic_brand(decision.correct_product_name_ar)
    for product in catalog:
        current_id = product.store_product_id
        same_identity = bool(
            (decision.correct_store_product_id and current_id == decision.correct_store_product_id)
            or (saved_en and normalize_english_brand(product.trusted_name_en) == saved_en)
            or (saved_ar and normalize_arabic_brand(product.name_ar) == saved_ar)
        )
        if not same_identity:
            continue
        compatibility = validate_product_compatibility(item.name, product.name_ar)
        if compatibility.accepted:
            compatible.append(product)
        else:
            rejected.append(compatibility.rejection_reason)
    if len(compatible) != 1:
        reason = (
            "Saved product is ambiguous in current Excel file"
            if len(compatible) > 1
            else (rejected[0] if rejected else "Saved product is absent from current Excel file")
        )
        _record_manual_rebind_failure(decision, target_key, catalog, reason)
        return MatchDecision(None, [], reason)

    product = compatible[0]
    identified = IdentifiedTarget(
        product,
        IdentityEvidence(
            "manual_review_rebound",
            saved_en or saved_ar,
            "saved approval rebound to current Excel catalog",
            1.0,
        ),
    )
    _record_manual_rebind(decision, target_key, product)
    rebound = _identity_decision(item, identified, time.perf_counter())
    return replace(rebound, source=DecisionSource.MANUAL_REVIEW_SAVED)


def _record_manual_rebind(decision, target_key: str, product: TargetProduct) -> None:
    """Update current catalog metadata while retaining the logical approval."""
    try:
        ManualReviewStore().upsert(
            replace(
                decision,
                correct_store_product_id=candidate_store_product_id(product.to_candidate_dict()),
                correct_product_name=product.trusted_name_en or decision.correct_product_name,
                correct_product_name_ar=product.name_ar,
                excel_target_key=target_key,
                excel_target_source_file=product.source_file,
                matching_source="excel-target",
                matching_source_label=(
                    f"{target_key}@{product.source_file}" if product.source_file else target_key
                ),
                last_rebind_status="compatible_rebound",
            )
        )
    except Exception:
        logger.warning("could not persist Excel-target manual-review rebound", exc_info=True)


def _record_manual_rebind_failure(
    decision, target_key: str, catalog: Sequence[TargetProduct], reason: str
) -> None:
    """Record why a saved approval could not bind to the current catalog."""
    try:
        source_files = sorted({product.source_file for product in catalog if product.source_file})
        source_file = source_files[0] if len(source_files) == 1 else ";".join(source_files)
        ManualReviewStore().upsert(
            replace(
                decision,
                excel_target_key=target_key,
                excel_target_source_file=source_file,
                matching_source="excel-target",
                matching_source_label=(
                    f"{target_key}@{source_file}" if source_file else target_key
                ),
                last_rebind_status=f"manual_review_required: {reason}",
            )
        )
    except Exception:
        logger.warning("could not persist Excel-target rebind failure", exc_info=True)


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
    item: Item,
    candidate_templates: Sequence[dict[str, Any]],
    config: MatchingConfig,
) -> MatchDecision:
    """Use the established threshold contract only for genuine English rows."""
    if not candidate_templates:
        return MatchDecision(None, [], "Arabic-only candidate lacks verified brand identity")
    candidates = [_copy_candidate_template(template) for template in candidate_templates]
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


def _copy_candidate_template(template: dict[str, Any]) -> dict[str, Any]:
    """Copy one cached candidate without sharing its mutable raw row."""
    candidate = dict(template)
    candidate["excelTargetRaw"] = dict(template["excelTargetRaw"])
    return candidate


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
