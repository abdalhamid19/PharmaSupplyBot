from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.coverage import build_coverage_records
from src.core.excel_target.excel_target_review_candidates import (
    ExcelTargetReviewCandidate,
    excel_target_row_key,
)
from src.core.excel_target.product_attributes import validate_product_compatibility
from src.core.utils.excel import Item
from scripts.baraka_coverage_report import build_enriched_coverage_rows


def test_coverage_report_distinguishes_identity_and_variant_rejection() -> None:
    products = [
        TargetProduct("1", "اينوديب شراب 100 مل", 10.0, 0.0),
        TargetProduct("2", "اينوديب 30 كبسول", 10.0, 0.0),
    ]
    def dictionary_lookup(brand: str):
        return [{"ar": "اينوديب", "en": "INODEP"}] if brand == "INODEP" else []

    with patch(
        "src.core.excel_target.excel_target_identity.lookup_en",
        side_effect=dictionary_lookup,
    ), patch(
        "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
        return_value={},
    ), patch(
        "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
        return_value={"rows": []},
    ):
        matcher = ExcelTargetMatcher("baraka", products)
        records = build_coverage_records(
            matcher,
            [
                Item("1", "INODEP CAPSULES 30", 1),
                Item("2", "UNKNOWN BRAND 10 MG", 1),
            ],
            MatchingConfig(),
        )

    assert records[0].coverage_category == "identity_compatible"
    assert records[0].identity_evidence_kind == "dictionary"
    assert records[0].compatible_count == 1
    assert records[1].coverage_category == "identity_absent"
    assert records[1].candidate_count == 0


def test_coverage_report_marks_known_identity_with_no_compatible_variant() -> None:
    product = TargetProduct("1", "اينوديب شراب 100 مل", 10.0, 0.0)
    with patch(
        "src.core.excel_target.excel_target_identity.lookup_en",
        return_value=[{"ar": "اينوديب", "en": "INODEP"}],
    ), patch(
        "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
        return_value={},
    ), patch(
        "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
        return_value={"rows": []},
    ):
        matcher = ExcelTargetMatcher("baraka", [product])
        record = build_coverage_records(
            matcher,
            [Item("1", "INODEP CAPSULES 30", 1)],
            MatchingConfig(),
        )[0]

    assert record.coverage_category == "identity_variant_rejected"
    assert record.compatible_count == 0
    assert record.compatibility_rejection == "candidate form conflicts with requested form"


def test_enriched_coverage_reports_total_and_saved_review_candidates() -> None:
    product = TargetProduct(
        "candidate-1",
        "INODEP SYRUP 100 ML",
        10.0,
        0.0,
        source_file="baraka.xlsx",
        source_row_number=17,
    )
    candidate = ExcelTargetReviewCandidate(
        target_key="baraka",
        product=product,
        score=91.5,
        compatibility=validate_product_compatibility(
            "INODEP CAPSULES 30", product.name_ar
        ),
        rejection_reason="candidate form conflicts with requested form",
    )
    matcher = SimpleNamespace(
        target_key="baraka",
        catalog=(product,),
        identity_index=SimpleNamespace(identify=lambda _name: ()),
        match=lambda _item, _config: SimpleNamespace(
            decision=SimpleNamespace(best_match=None, final_reason="no verified identity"),
            review_candidates=(candidate,),
        ),
    )

    rows = build_enriched_coverage_rows(
        matcher, [Item("1", "INODEP CAPSULES 30", 1)], MatchingConfig()
    )

    row = rows[0]
    assert row["review_candidate_count_total"] == 1
    assert row["review_candidate_count_saved"] == 1
    assert row["review_candidate_methods"] == ""
    assert row["review_candidate_scores"] == "91.50"
    assert row["coverage_category"] == "excel_target_candidate_available"
    assert row["manual_review_required"] is True
    assert row["candidate_row_keys"] == excel_target_row_key("baraka", product)


def test_coverage_candidate_reporting_does_not_call_translation_provider(
    monkeypatch,
) -> None:
    matcher = SimpleNamespace(
        target_key="baraka",
        catalog=(),
        identity_index=SimpleNamespace(identify=lambda _name: ()),
        match=lambda _item, _config: SimpleNamespace(
            decision=SimpleNamespace(best_match=None, final_reason="identity absent"),
            review_candidates=(),
        ),
    )
    monkeypatch.setattr(
        "src.core.normalization.translation.ar_to_en_many",
        lambda _names: (_ for _ in ()).throw(
            AssertionError("coverage reporting must not call Cohere")
        ),
    )
    monkeypatch.setattr(
        "src.core.database.translation_cache.TranslationCache.put_many",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("coverage reporting must not write the cache")
        ),
    )

    rows = build_enriched_coverage_rows(
        matcher, [Item("1", "UNKNOWN", 1)], MatchingConfig()
    )

    assert rows[0]["review_candidate_count_total"] == 0
