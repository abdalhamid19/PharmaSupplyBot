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
from src.core.manual_review.manual_review_store_helpers import (
    is_scoped_excel_target_approval,
)
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
    excel_target_row_key,
)
from .excel_target_review_discovery import (
    ExcelTargetReviewDiscoveryIndex,
    ReviewDiscoveryConfig,
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
    """Reusable matcher whose optional live translation runs only at index build."""

    def __init__(
        self,
        target_key: str,
        catalog: Sequence[TargetProduct],
        *,
        allow_live_translation: bool = False,
        use_saved_approvals: bool = True,
    ) -> None:
        self.target_key = target_key
        self.catalog = tuple(catalog)
        # Counterfactual analysis and offline evaluation must be able to
        # replay ordinary matching without the saved-review short circuit.
        # Keeping this explicit on the matcher prevents an injected analysis
        # path from accidentally writing/rebinding manual-review decisions.
        self.use_saved_approvals = bool(use_saved_approvals)
        self.identity_index = ExcelTargetBilingualIndex.build(
            self.catalog,
            allow_live_translation=allow_live_translation,
        )
        self.review_discovery = ExcelTargetReviewDiscoveryIndex.build(self.catalog)
        self._catalog_by_id = _catalog_products_by_id(self.catalog)
        self._native_english_candidate_templates = tuple(
            product.to_candidate_dict()
            for product in self.catalog
            if product.trusted_name_en
        )

    def match(self, item: Item, config: MatchingConfig) -> ExcelTargetMatch:
        started = time.perf_counter()
        if not self.catalog:
            return _empty_match(self.target_key)

        if self.use_saved_approvals:
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
        discovery_hits = self.review_discovery.discover(
            item,
            config=_review_discovery_config(config),
        )
        review_candidates = build_review_candidates(
            item,
            self.target_key,
            self.catalog,
            identified=identified,
            diagnostics=decision.diagnostics,
            discovery_hits=discovery_hits,
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
    *,
    allow_live_translation: bool = False,
    use_saved_approvals: bool = True,
) -> ExcelTargetMatch:
    """Compatibility wrapper; batch callers must reuse :class:`ExcelTargetMatcher`."""
    return ExcelTargetMatcher(
        target_key,
        catalog,
        allow_live_translation=allow_live_translation,
        use_saved_approvals=use_saved_approvals,
    ).match(item, matching_config)


def match_item_against_all_targets(
    item: Item,
    app_config: AppConfig,
    catalogs: dict[str, list[TargetProduct]],
    *,
    allow_live_translation: bool = False,
    use_saved_approvals: bool = True,
) -> dict[str, ExcelTargetMatch]:
    matchers = {
        target_key: ExcelTargetMatcher(
            target_key,
            catalog,
            allow_live_translation=allow_live_translation,
            use_saved_approvals=use_saved_approvals,
        )
        for target_key, catalog in catalogs.items()
    }
    return {
        target_key: matcher.match(item, app_config.matching)
        for target_key, matcher in matchers.items()
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
        if candidate.evidence.kind == "cohere_translation":
            rejected.append("Cohere identity requires manual review under safe policy")
            continue
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

    if decision.excel_target_row_key:
        return _scoped_row_approval(item, target_key, catalog, decision)

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


def _scoped_row_approval(
    item: Item,
    target_key: str,
    catalog: Sequence[TargetProduct],
    decision,
) -> MatchDecision | None:
    """Apply a human approval to exactly one saved Excel target row.

    A scoped approval is the only path allowed to override a variant conflict.
    The row key includes target, source file, row number, code, and name, so a
    changed or duplicated workbook row cannot inherit an old approval.
    """
    matches = [
        product
        for product in catalog
        if excel_target_row_key(target_key, product) == decision.excel_target_row_key
    ]
    if len(matches) != 1:
        reason = (
            "Saved approved Excel row is ambiguous in current Excel file"
            if len(matches) > 1
            else "Saved approved Excel row is absent from current Excel file"
        )
        _record_manual_rebind_failure(decision, target_key, catalog, reason)
        return None

    product = matches[0]
    if not is_scoped_excel_target_approval(
        decision,
        target_key=target_key,
        source_file=product.source_file,
        source_row=product.source_row_number,
        row_key=decision.excel_target_row_key,
    ):
        reason = "Saved approved Excel row scope does not match current target row"
        _record_manual_rebind_failure(decision, target_key, catalog, reason)
        return None
    if (
        decision.correct_store_product_id
        and decision.correct_store_product_id != product.store_product_id
    ):
        reason = "Saved approved Excel row product id changed"
        _record_manual_rebind_failure(decision, target_key, catalog, reason)
        return None

    compatibility = validate_product_compatibility(item.name, product.name_ar)
    identified = IdentifiedTarget(
        product,
        IdentityEvidence(
            "manual_review_rebound",
            normalize_english_brand(product.trusted_name_en)
            or normalize_arabic_brand(product.name_ar),
            "saved approved_match rebound to exact Excel target row",
            1.0,
        ),
    )
    _record_manual_rebind(
        decision,
        target_key,
        product,
        rebind_status="approved_manual_override",
    )
    rebound = _identity_decision(item, identified, time.perf_counter())
    if rebound.best_match is not None:
        rebound.best_match.data.update(
            {
                "compatibility_status": "approved_manual_override",
                "compatibility_rejection": compatibility.rejection_reason,
                "manual_override": True,
            }
        )
    return replace(
        rebound,
        source=DecisionSource.MANUAL_REVIEW_SAVED,
        final_reason=(
            "Excel-target approved_manual_override: saved approved_match "
            "rebound to exact target row"
        ),
    )


def _record_manual_rebind(
    decision,
    target_key: str,
    product: TargetProduct,
    *,
    rebind_status: str = "compatible_rebound",
) -> None:
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
                excel_target_row_key=excel_target_row_key(target_key, product),
                excel_target_source_row=int(product.source_row_number or 0),
                last_rebind_status=rebind_status,
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
    if evidence.kind == "review_fuzzy":
        raise ValueError("review_fuzzy evidence cannot produce an automatic match")
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


def _catalog_products_by_id(
    catalog: Sequence[TargetProduct],
) -> dict[str, tuple[TargetProduct, ...]]:
    products_by_id: dict[str, list[TargetProduct]] = {}
    for product in catalog:
        product_id = product.store_product_id
        products_by_id.setdefault(product_id, []).append(product)
    return {key: tuple(value) for key, value in products_by_id.items()}


def _review_discovery_config(config: MatchingConfig) -> ReviewDiscoveryConfig:
    """Translate app matching settings into the review-only discovery contract."""
    return ReviewDiscoveryConfig(
        enabled=bool(getattr(config, "excel_target_review_candidates_enabled", True)),
        limit=int(getattr(config, "excel_target_review_candidate_limit", 5)),
        strong_score=float(
            getattr(config, "excel_target_review_fuzzy_strong_score", 90.0)
        ),
        strong_margin=float(
            getattr(config, "excel_target_review_fuzzy_strong_margin", 8.0)
        ),
        medium_score=float(
            getattr(config, "excel_target_review_fuzzy_medium_score", 86.0)
        ),
        medium_margin=float(
            getattr(config, "excel_target_review_fuzzy_medium_margin", 12.0)
        ),
        ambiguous_score=float(
            getattr(config, "excel_target_review_ambiguous_score", 88.0)
        ),
        ambiguous_margin=float(
            getattr(config, "excel_target_review_ambiguous_margin", 8.0)
        ),
    )


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
