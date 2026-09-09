from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.approved_correction_analysis import (
    analyze_approved_corrections,
    catalog_fingerprint,
)
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatch
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.excel_target_review_candidates import excel_target_row_key
from src.core.manual_review.manual_review_store import ManualReviewDecision
from src.core.matching_types import MatchDecision, SearchMatch
from src.core.utils.excel import Item


TARGET_KEY = "baraka"
SOURCE_FILE = "baraka.xlsx"


def _product(
    code: str = "row-1",
    name: str = "INODEP CAPSULES 30",
    *,
    row: int = 2,
) -> TargetProduct:
    return TargetProduct(code, name, 10.0, 0.0, SOURCE_FILE, source_row_number=row)


def _decision(
    item_name: str = "INODEP CAPSULES 30",
    *,
    target_key: str = TARGET_KEY,
    product: TargetProduct | None = None,
    item_code: str = "item-1",
    **kwargs,
) -> ManualReviewDecision:
    product = product or _product()
    values = dict(
        approved=True,
        correct_store_product_id=product.store_product_id,
        correct_product_name=product.trusted_name_en or product.name,
        correct_product_name_ar=product.name_ar,
        run_id="run-1",
        manual_decision="approved_match",
        excel_target_key=target_key,
        excel_target_source_file=product.source_file,
        matching_source="excel-target",
        matching_source_label=f"{target_key}@{product.source_file}",
        excel_target_row_key=excel_target_row_key(target_key, product),
        excel_target_source_row=product.source_row_number,
    )
    values.update(kwargs)
    return ManualReviewDecision(
        item_code=item_code,
        item_name=item_name,
        **values,
    )


@dataclass
class _Matcher:
    decision: MatchDecision
    review_candidates: tuple = ()

    def match(self, item: Item, config: MatchingConfig) -> ExcelTargetMatch:
        return ExcelTargetMatch(TARGET_KEY, self.decision, 1, self.review_candidates)


def _factory_for(decision: MatchDecision, calls: list[dict]) :
    def factory(target_key, catalog, **kwargs):
        calls.append({"target_key": target_key, "catalog": catalog, **kwargs})
        return _Matcher(decision)

    return factory


def test_identity_absent_approval_is_replayed_without_saved_approval() -> None:
    product = _product()
    approval = _decision(product=product)
    calls: list[dict] = []

    report = analyze_approved_corrections(
        [approval],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(
            MatchDecision(None, [], "Arabic-only candidate lacks verified brand identity"),
            calls,
        ),
    )

    assert len(report.findings) == 1
    finding = report.findings[0]
    assert finding.root_cause == "identity_absent"
    assert finding.approval_status == "applied"
    assert finding.match_origin == "approved_manual_override"
    assert finding.row_key == approval.excel_target_row_key
    assert finding.catalog_fingerprint == catalog_fingerprint(TARGET_KEY, [product])
    assert calls and calls[0]["use_saved_approvals"] is False


def test_approved_decision_is_filtered_by_source_and_status() -> None:
    product = _product()
    tawreed = ManualReviewDecision("x", "X", True, "id", manual_decision="approved_match")
    rejected = _decision(product=product, approved=False, manual_decision="needs_correction")
    report = analyze_approved_corrections(
        [tawreed, rejected],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(MatchDecision(None, [], "No match"), []),
    )
    assert report.findings == ()


def test_variant_conflict_has_priority_over_missing_identity() -> None:
    product = _product(name="INODEP SYRUP 100 ML")
    approval = _decision("INODEP CAPSULES 30", product=product)
    report = analyze_approved_corrections(
        [approval],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(MatchDecision(None, [], "Arabic-only candidate lacks verified brand identity"), []),
    )
    assert report.findings[0].root_cause == "variant_conflict"


def test_stale_row_and_wrong_target_are_invalid_scope_findings() -> None:
    product = _product()
    stale = _decision(product=product, excel_target_row_key="old-row")
    wrong_target = _decision(product=product, target_key="kaisr")
    report = analyze_approved_corrections(
        [stale, wrong_target],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(MatchDecision(None, [], "No match"), []),
    )
    assert [f.root_cause for f in report.findings] == [
        "stale_or_missing_row",
        "source_scope_mismatch",
    ]
    assert all(f.approval_status == "stale" for f in report.findings)


def test_duplicate_current_row_is_reported_as_ambiguous() -> None:
    product = _product()
    duplicate = _product()
    approval = _decision(product=product)
    report = analyze_approved_corrections(
        [approval],
        {TARGET_KEY: [product, duplicate]},
        MatchingConfig(),
        _factory_for(MatchDecision(None, [], "Ambiguous verified Excel-target candidates"), []),
    )
    assert report.findings[0].root_cause == "ambiguous_identity"


def test_counterfactual_match_is_not_reported_as_learning_failure() -> None:
    product = _product()
    approval = _decision(product=product)
    matched = MatchDecision(
        SearchMatch("INODEP CAPSULES 30", 0, 20.0, product.to_candidate_dict()),
        [],
        "Excel-target verified native_english",
    )
    report = analyze_approved_corrections(
        [approval],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(matched, []),
    )
    finding = report.findings[0]
    assert finding.root_cause == "unexpected_counterfactual_match"
    assert finding.match_origin == "automatic_verified"
    assert report.counts_by_root_cause["unexpected_counterfactual_match"] == 1


def test_repeated_cohere_only_findings_create_human_gated_recommendation() -> None:
    product = _product()
    approvals = [
        _decision(
            product=product,
            item_code=f"item-{index}",
            identity_evidence_kind="cohere_translation",
        )
        for index in range(2)
    ]
    report = analyze_approved_corrections(
        approvals,
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(
            MatchDecision(
                None,
                [],
                "Cohere identity requires manual review under safe policy",
            ),
            [],
        ),
    )
    assert len(report.recommendations) == 1
    recommendation = report.recommendations[0]
    assert recommendation.root_cause == "cohere_review_only"
    assert recommendation.requires_human_approval is True
    assert "keep Cohere-only matches manual" in recommendation.recommendation


def test_approval_outside_current_input_is_not_a_matching_failure() -> None:
    product = _product()
    approval = _decision(product=product)
    report = analyze_approved_corrections(
        [approval],
        {TARGET_KEY: [product]},
        MatchingConfig(),
        _factory_for(MatchDecision(None, [], "No match"), []),
        order_items=[Item("other", "OTHER", 1)],
    )
    finding = report.findings[0]
    assert finding.root_cause == "approval_outside_current_input"
    assert finding.approval_status == "invalid"
    assert finding.match_origin == "approval_outside_current_input"


def test_matcher_can_disable_saved_approval_lookup_and_rebind_writes() -> None:
    product = _product()
    matcher = ExcelTargetMatcher(TARGET_KEY, [product], use_saved_approvals=False)
    item = Item("item-1", product.name, 1)
    with (
        patch(
            "src.core.excel_target.excel_target_matching.saved_manual_review_decision"
        ) as saved_lookup,
        patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind"
        ) as rebind,
        patch(
            "src.core.excel_target.excel_target_matching._record_manual_rebind_failure"
        ) as rebind_failure,
    ):
        matcher.match(item, MatchingConfig())
    saved_lookup.assert_not_called()
    rebind.assert_not_called()
    rebind_failure.assert_not_called()
