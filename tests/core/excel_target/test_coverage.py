from __future__ import annotations

from unittest.mock import patch

from src.core.config.config_models import MatchingConfig
from src.core.excel_target.excel_target_loader import TargetProduct
from src.core.excel_target.excel_target_matching import ExcelTargetMatcher
from src.core.excel_target.coverage import build_coverage_records
from src.core.utils.excel import Item


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
