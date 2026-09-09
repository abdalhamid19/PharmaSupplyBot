"""Read-only counterfactual analysis of approved Excel-target corrections.

Saved approvals are useful labels for understanding missed matches, but they
must never become implicit fuzzy-match rules.  This module replays each
approved, row-scoped decision against a matcher with the saved-review seam
disabled and records the first safety gate that would have stopped it.

The analyzer deliberately accepts snapshots and injected matcher factories. It
does not open a database, call a translation provider, or write a decision
back to :class:`ManualReviewStore`.
"""

from __future__ import annotations

import hashlib
import inspect
import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence

from src.core.config.config_models import MatchingConfig
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.utils.excel import Item

from .excel_target_loader import TargetProduct
from .excel_target_matching import ExcelTargetMatch, ExcelTargetMatcher
from .excel_target_review_candidates import excel_target_row_key
from .product_attributes import validate_product_compatibility


ApprovalStatus = Literal["applied", "stale", "invalid"]


@dataclass(frozen=True)
class ApprovedCorrectionFinding:
    """Immutable evidence for one approved correction in the audit report."""

    item_code: str
    item_name: str
    target_key: str
    row_key: str
    excel_target_source_file: str
    excel_target_source_row: int
    approval_run_id: str
    catalog_fingerprint: str
    approval_status: ApprovalStatus
    counterfactual_status: str
    root_cause: str
    original_reason: str
    counterfactual_reason: str
    final_reason: str
    compatibility_status: str
    candidate_method: str
    candidate_count_total: int
    decision_source: str
    match_origin: str


@dataclass(frozen=True)
class RuleRecommendation:
    """A deterministic, human-gated candidate improvement group."""

    target_key: str
    root_cause: str
    evidence_count: int
    recommendation: str
    sample_item_keys: tuple[str, ...] = ()
    sample_row_keys: tuple[str, ...] = ()
    requires_human_approval: bool = True


@dataclass(frozen=True)
class ApprovedCorrectionReport:
    """Complete read-only report for a snapshot of approved corrections."""

    findings: tuple[ApprovedCorrectionFinding, ...]
    counts_by_root_cause: Mapping[str, int]
    recommendations: tuple[RuleRecommendation, ...]
    counts_by_match_origin: Mapping[str, int] = field(default_factory=dict)
    catalog_fingerprints: Mapping[str, str] = field(default_factory=dict)


MatcherFactory = Callable[..., Any]


def catalog_fingerprint(
    target_key: str,
    catalog: Sequence[TargetProduct],
) -> str:
    """Return a stable SHA-256 fingerprint for the loaded target rows.

    Price and discount are intentionally excluded: they are not row identity
    and a price-only workbook refresh should not invalidate an approval.  The
    source path, physical row, stable product id, and both names are included
    so a report can prove which catalog snapshot it analyzed.
    """

    rows = [
        {
            "target_key": str(target_key),
            "source_file": str(product.source_file or ""),
            "source_row": int(product.source_row_number or 0),
            "store_product_id": str(product.store_product_id or ""),
            "name_ar": str(product.name_ar or ""),
            "trusted_name_en": str(product.trusted_name_en or ""),
        }
        for product in catalog
    ]
    rows.sort(
        key=lambda row: (
            row["target_key"],
            row["source_file"].casefold(),
            row["source_row"],
            row["store_product_id"],
            row["name_ar"],
            row["trusted_name_en"],
        )
    )
    canonical = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def analyze_approved_corrections(
    decisions: Iterable[ManualReviewDecision],
    catalogs: Mapping[str, Sequence[TargetProduct]],
    matching_config: MatchingConfig,
    matcher_factory: MatcherFactory | None = None,
    *,
    order_items: Iterable[Item] | None = None,
) -> ApprovedCorrectionReport:
    """Analyze approved Excel-target decisions using approval-disabled replay.

    ``decisions`` is a read-only snapshot.  ``matcher_factory`` is injected so
    callers can use a fake matcher in tests or a prebuilt offline matcher in a
    report command.  The analyzer requests ``use_saved_approvals=False`` when
    the factory exposes that keyword; an ordinary two-argument factory is also
    supported for lightweight test doubles.
    """

    if isinstance(decisions, Mapping):
        decision_values = list(decisions.values())
    else:
        decision_values = list(decisions)
    factory = matcher_factory or _default_matcher_factory
    current_items = None
    if order_items is not None:
        current_items = {_item_key(item) for item in order_items}

    fingerprints = {
        str(target_key): catalog_fingerprint(str(target_key), tuple(catalog))
        for target_key, catalog in catalogs.items()
    }
    findings: list[ApprovedCorrectionFinding] = []
    for decision in decision_values:
        if not _is_approved_excel_target(decision):
            continue
        target_key = str(decision.excel_target_key or "")
        catalog = tuple(catalogs.get(target_key, ()))
        fingerprint = fingerprints.get(target_key, "")
        if current_items is not None and _decision_key(decision) not in current_items:
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint=fingerprint,
                    root_cause="approval_outside_current_input",
                    status="invalid",
                    counterfactual_status="not_replayed",
                    reason="Approval is outside the supplied order-item dataset",
                    catalog_size=len(catalog),
                )
            )
            continue

        if not _has_complete_provenance(decision):
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint=fingerprint,
                    root_cause="legacy_invalid",
                    status="invalid",
                    counterfactual_status="not_replayed",
                    reason="Approved correction lacks complete Excel row provenance",
                    catalog_size=len(catalog),
                )
            )
            continue

        if target_key not in catalogs:
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint="",
                    root_cause="source_scope_mismatch",
                    status="stale",
                    counterfactual_status="not_replayed",
                    reason="Approval target key is not present in supplied catalogs",
                    catalog_size=0,
                )
            )
            continue

        row_matches = [
            product
            for product in catalog
            if excel_target_row_key(target_key, product)
            == decision.excel_target_row_key
        ]
        if len(row_matches) == 0:
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint=fingerprint,
                    root_cause="stale_or_missing_row",
                    status="stale",
                    counterfactual_status="stale",
                    reason="Approved Excel row key is absent from current catalog",
                    catalog_size=len(catalog),
                )
            )
            continue
        if len(row_matches) > 1:
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint=fingerprint,
                    root_cause="ambiguous_identity",
                    status="stale",
                    counterfactual_status="ambiguous",
                    reason="Approved Excel row key binds to duplicate current rows",
                    catalog_size=len(catalog),
                )
            )
            continue
        product = row_matches[0]
        if not _row_provenance_matches(decision, target_key, product):
            findings.append(
                _invalid_finding(
                    decision,
                    target_key=target_key,
                    catalog_fingerprint=fingerprint,
                    root_cause="stale_or_missing_row",
                    status="stale",
                    counterfactual_status="stale",
                    reason="Approved Excel row provenance changed in current catalog",
                    catalog_size=len(catalog),
                )
            )
            continue

        item = Item(str(decision.item_code or ""), str(decision.item_name or ""), 1)
        matcher = _build_approval_disabled_matcher(factory, target_key, catalog)
        replay = matcher.match(item, matching_config)
        findings.append(
            _finding_from_replay(
                decision,
                product,
                target_key,
                fingerprint,
                catalog,
                replay,
                item,
            )
        )

    findings_tuple = tuple(findings)
    root_counts = Counter(finding.root_cause for finding in findings_tuple)
    origin_counts = Counter(finding.match_origin for finding in findings_tuple)
    return ApprovedCorrectionReport(
        findings=findings_tuple,
        counts_by_root_cause=dict(sorted(root_counts.items())),
        recommendations=_recommendations(findings_tuple),
        counts_by_match_origin=dict(sorted(origin_counts.items())),
        catalog_fingerprints=dict(sorted(fingerprints.items())),
    )


def _default_matcher_factory(
    target_key: str,
    catalog: Sequence[TargetProduct],
    *,
    use_saved_approvals: bool = False,
) -> ExcelTargetMatcher:
    return ExcelTargetMatcher(
        target_key,
        catalog,
        use_saved_approvals=use_saved_approvals,
    )


def _build_approval_disabled_matcher(
    factory: MatcherFactory,
    target_key: str,
    catalog: Sequence[TargetProduct],
) -> Any:
    """Construct an approval-disabled matcher while supporting test doubles."""

    try:
        signature = inspect.signature(factory)
        parameters = signature.parameters.values()
        accepts_keyword = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            or parameter.name == "use_saved_approvals"
            for parameter in parameters
        )
    except (TypeError, ValueError):
        accepts_keyword = True
    if accepts_keyword:
        return factory(target_key, catalog, use_saved_approvals=False)
    matcher = factory(target_key, catalog)
    # A production matcher always exposes the seam.  Test doubles may omit it
    # because they cannot observe saved decisions; they remain valid here.
    if hasattr(matcher, "use_saved_approvals"):
        try:
            setattr(matcher, "use_saved_approvals", False)
        except Exception:
            pass
    return matcher


def _is_approved_excel_target(decision: Any) -> bool:
    source = str(getattr(decision, "matching_source", "") or "").strip().casefold()
    source = source.replace("_", "-")
    return bool(
        source == "excel-target"
        and getattr(decision, "approved", False) is True
        and str(getattr(decision, "manual_decision", "") or "")
        == "approved_match"
    )


def _has_complete_provenance(decision: Any) -> bool:
    return bool(
        str(getattr(decision, "excel_target_key", "") or "").strip()
        and str(getattr(decision, "excel_target_source_file", "") or "").strip()
        and str(getattr(decision, "excel_target_row_key", "") or "").strip()
        and int(getattr(decision, "excel_target_source_row", 0) or 0) > 0
    )


def _row_provenance_matches(
    decision: Any,
    target_key: str,
    product: TargetProduct,
) -> bool:
    return (
        str(getattr(decision, "excel_target_source_file", "") or "").replace("\\", "/").casefold()
        == str(product.source_file or "").replace("\\", "/").casefold()
        and int(getattr(decision, "excel_target_source_row", 0) or 0)
        == int(product.source_row_number or 0)
        and str(getattr(decision, "excel_target_row_key", "") or "")
        == excel_target_row_key(target_key, product)
    )


def _decision_key(decision: Any) -> tuple[str, str]:
    return (
        _normalize_key(getattr(decision, "item_code", "")),
        _normalize_key(getattr(decision, "item_name", "")),
    )


def _item_key(item: Item) -> tuple[str, str]:
    return (_normalize_key(item.code), _normalize_key(item.name))


def _normalize_key(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _finding_from_replay(
    decision: Any,
    product: TargetProduct,
    target_key: str,
    fingerprint: str,
    catalog: Sequence[TargetProduct],
    replay: ExcelTargetMatch,
    item: Item,
) -> ApprovedCorrectionFinding:
    match_decision = replay.decision
    final_reason = str(getattr(match_decision, "final_reason", "") or "")
    compatibility = validate_product_compatibility(item.name, product.name_ar)
    root_cause = _classify_root_cause(
        match_decision,
        replay,
        compatibility.accepted,
        product,
    )
    ordinary_match = match_decision.best_match is not None
    match_origin = "automatic_verified" if ordinary_match else "approved_manual_override"
    return ApprovedCorrectionFinding(
        item_code=str(decision.item_code or ""),
        item_name=str(decision.item_name or ""),
        target_key=target_key,
        row_key=str(decision.excel_target_row_key or ""),
        excel_target_source_file=str(decision.excel_target_source_file or ""),
        excel_target_source_row=int(decision.excel_target_source_row or 0),
        approval_run_id=str(decision.run_id or ""),
        catalog_fingerprint=fingerprint,
        approval_status="applied",
        counterfactual_status="matched" if ordinary_match else "unmatched",
        root_cause=root_cause,
        original_reason=_original_reason(decision),
        counterfactual_reason=final_reason,
        final_reason=final_reason,
        compatibility_status="compatible" if compatibility.accepted else "rejected",
        candidate_method=_candidate_method(decision, match_decision, replay),
        candidate_count_total=len(catalog),
        decision_source=_decision_source(match_decision),
        match_origin=match_origin,
    )


def _classify_root_cause(
    decision: Any,
    replay: ExcelTargetMatch,
    target_compatible: bool,
    product: TargetProduct,
) -> str:
    reason = str(getattr(decision, "final_reason", "") or "").casefold()
    if not target_compatible:
        return "variant_conflict"
    candidates = tuple(getattr(replay, "review_candidates", ()) or ())
    if "ambiguous" in reason or sum(
        1 for candidate in candidates if getattr(candidate, "review_status", "") == "ambiguous"
    ) > 1:
        return "ambiguous_identity"
    if "cohere" in reason or any(
        "cohere" in str(getattr(candidate, "identity_evidence_kind", "")).casefold()
        for candidate in candidates
    ):
        return "cohere_review_only"
    if _looks_like_native_score_failure(decision, product):
        return "native_score_below_threshold"
    if decision.best_match is not None:
        return "unexpected_counterfactual_match"
    return "identity_absent"


def _looks_like_native_score_failure(decision: Any, product: TargetProduct) -> bool:
    if not product.trusted_name_en:
        return False
    reason = str(getattr(decision, "final_reason", "") or "").casefold()
    if any(
        phrase in reason
        for phrase in (
            "arabic-only",
            "lacks verified brand identity",
            "cohere",
            "identity absent",
        )
    ):
        return False
    diagnostics = tuple(getattr(decision, "diagnostics", ()) or ())
    return bool(diagnostics) or any(
        phrase in reason
        for phrase in ("score", "candidate", "threshold", "semantic token")
    )


def _candidate_method(
    approval: Any,
    decision: Any,
    replay: ExcelTargetMatch,
) -> str:
    explicit = str(getattr(approval, "candidate_method", "") or "")
    if explicit:
        return explicit
    best = getattr(decision, "best_match", None)
    if best is not None:
        return str(best.data.get("identity_evidence_kind", "") or "")
    candidates = tuple(getattr(replay, "review_candidates", ()) or ())
    return str(getattr(candidates[0], "candidate_method", "") or "") if candidates else ""


def _decision_source(decision: Any) -> str:
    source = getattr(decision, "source", "")
    return str(getattr(source, "value", source) or "")


def _original_reason(decision: Any) -> str:
    return str(
        getattr(decision, "identity_evidence", "")
        or getattr(decision, "last_rebind_status", "")
        or getattr(decision, "candidate_method", "")
        or "approved_match"
    )


def _invalid_finding(
    decision: Any,
    *,
    target_key: str,
    catalog_fingerprint: str,
    root_cause: str,
    status: ApprovalStatus,
    counterfactual_status: str,
    reason: str,
    catalog_size: int,
) -> ApprovedCorrectionFinding:
    return ApprovedCorrectionFinding(
        item_code=str(getattr(decision, "item_code", "") or ""),
        item_name=str(getattr(decision, "item_name", "") or ""),
        target_key=target_key,
        row_key=str(getattr(decision, "excel_target_row_key", "") or ""),
        excel_target_source_file=str(
            getattr(decision, "excel_target_source_file", "") or ""
        ),
        excel_target_source_row=int(
            getattr(decision, "excel_target_source_row", 0) or 0
        ),
        approval_run_id=str(getattr(decision, "run_id", "") or ""),
        catalog_fingerprint=catalog_fingerprint,
        approval_status=status,
        counterfactual_status=counterfactual_status,
        root_cause=root_cause,
        original_reason=_original_reason(decision),
        counterfactual_reason=reason,
        final_reason=reason,
        compatibility_status="unknown",
        candidate_method=str(getattr(decision, "candidate_method", "") or ""),
        candidate_count_total=catalog_size,
        decision_source="",
        match_origin=(
            "approval_outside_current_input"
            if root_cause == "approval_outside_current_input"
            else "stale_or_invalid"
        ),
    )


def _recommendations(
    findings: Sequence[ApprovedCorrectionFinding],
) -> tuple[RuleRecommendation, ...]:
    groups: dict[tuple[str, str], list[ApprovedCorrectionFinding]] = {}
    for finding in findings:
        if finding.root_cause not in {"identity_absent", "native_score_below_threshold"}:
            continue
        groups.setdefault((finding.target_key, finding.root_cause), []).append(finding)
    recommendations: list[RuleRecommendation] = []
    for (target_key, root_cause), group in sorted(groups.items()):
        if len(group) < 2:
            continue
        recommendation = (
            "Review deterministic alias/normalization evidence and add gold cases"
            if root_cause == "identity_absent"
            else "Review exact normalized alias evidence against native score gates"
        )
        recommendations.append(
            RuleRecommendation(
                target_key=target_key,
                root_cause=root_cause,
                evidence_count=len(group),
                recommendation=recommendation,
                sample_item_keys=tuple(
                    f"{finding.item_code}:{finding.item_name}" for finding in group[:10]
                ),
                sample_row_keys=tuple(finding.row_key for finding in group[:10]),
                requires_human_approval=True,
            )
        )
    return tuple(recommendations)


__all__ = [
    "ApprovedCorrectionFinding",
    "ApprovedCorrectionReport",
    "RuleRecommendation",
    "analyze_approved_corrections",
    "catalog_fingerprint",
]
