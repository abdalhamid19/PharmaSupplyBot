"""Focused public contracts for audited Excel-target Arabic normalization."""

from __future__ import annotations

from unittest.mock import patch

from src.core.excel_target.excel_target_identity import (
    ExcelTargetBilingualIndex,
    normalize_arabic_brand,
    normalize_arabic_review_brand,
)
from src.core.excel_target.excel_target_loader import TargetProduct


def test_closol_spray_and_millilitre_spellings_share_a_brand_key() -> None:
    tawreed_key = normalize_arabic_brand(
        "\u0643\u0644\u0648\u0633\u0648\u0644 \u0633\u0628\u0631\u0627\u0649 50\u0645\u0644\u0644\u0649"
    )
    target_key = normalize_arabic_brand(
        "\u0643\u0644\u0648\u0633\u0648\u0644 \u0628\u062e\u0627\u062e \u0645\u0648\u0636\u0639\u064a 50 \u0645\u0644"
    )
    tawreed_topical_key = normalize_arabic_brand(
        "\u0643\u0644\u0648\u0633\u0648\u0644 10 \u0645\u062c\u0645 / \u0645\u0644 \u0628\u062e\u0627\u062e \u0645\u0648\u0636\u0639\u064a 50 \u0645\u0644"
    )

    assert tawreed_key == target_key == tawreed_topical_key == "\u0643\u0644\u0648\u0633\u0648\u0644"
    assert normalize_arabic_brand("\u0628\u0631\u0627\u0646\u062f \u0645\u0644") == "\u0628\u0631\u0627\u0646\u062f \u0645\u0644"


def test_regcor_legacy_status_token_is_ignored_only_after_catalog_attributes() -> None:
    assert normalize_arabic_brand(
        "\u0631\u064a\u062c\u0643\u0648\u0631 10\u0645\u062c\u0645 10\u0642\u0631\u0635 \u0642\u062f\u064a\u0645"
    ) == normalize_arabic_brand(
        "\u0631\u064a\u062c\u0643\u0648\u0631 10 \u0645\u062c\u0645 10 \u0627\u0642\u0631\u0627\u0635"
    ) == "\u0631\u064a\u062c\u0643\u0648\u0631"

    assert normalize_arabic_brand("\u0631\u064a\u062c\u0643\u0648\u0631 \u0642\u062f\u064a\u0645") == (
        "\u0631\u064a\u062c\u0643\u0648\u0631 \u0642\u062f\u064a\u0645"
    )


def test_ator_catalog_suffix_is_removed_only_for_an_at_or_variant_with_attributes() -> None:
    assert normalize_arabic_brand(
        "\u0627\u062a\u0648\u0631 20\u0645\u062c\u064510\u0642\u0631\u0635 \u0633"
    ) == normalize_arabic_brand(
        "\u0627\u062a\u0648\u0631 20 \u0645\u062c\u0645 10 \u0627\u0642\u0631\u0627\u0635"
    ) == "\u0627\u062a\u0648\u0631"

    assert normalize_arabic_brand("\u0627\u062a\u0648\u0631 \u0633") == "\u0627\u062a\u0648\u0631 \u0633"
    assert normalize_arabic_brand(
        "\u0627\u062a\u0648\u0631\u0633 20 \u0645\u062c\u0645 10 \u0627\u0642\u0631\u0627\u0635"
    ) == "\u0627\u062a\u0648\u0631\u0633"


def test_adolor_ampoule_singular_and_plural_share_a_brand_key() -> None:
    assert normalize_arabic_brand(
        "\u0627\u062f\u0648\u0644\u0648\u0631 30\u0645\u062c\u0645 3 \u0627\u0645\u0628\u0648\u0644\u0627\u062a"
    ) == normalize_arabic_brand(
        "\u0627\u062f\u0648\u0644\u0648\u0631 30 \u0645\u062c\u0645 3 \u0627\u0645\u0628\u0648\u0644"
    ) == "\u0627\u062f\u0648\u0644\u0648\u0631"


def test_lactase_drop_descriptors_share_a_brand_key_without_losing_strength() -> None:
    assert normalize_arabic_brand(
        "\u0644\u0627\u0643\u062a\u064a\u0632 1000 \u0645\u062c\u0645 \u0642\u0637\u0631\u0647 \u0628\u0627\u0644\u0641\u0645 15 \u0645\u0644"
    ) == normalize_arabic_brand(
        "\u0644\u0627\u0643\u062a\u064a\u0632 1000 \u0646\u0642\u0637 15 \u0645\u0644"
    ) == "\u0644\u0627\u0643\u062a\u064a\u0632"


def test_review_brand_normalization_removes_fused_ampoule_and_status_suffix() -> None:
    assert normalize_arabic_review_brand(
        "\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646 3\u0645\u0628\u0648\u0644 \u0633 \u062c\u062f\u064a\u062f"
    ) == "\u0641\u0648\u0644\u062a\u0627\u0631\u064a\u0646"


def test_review_brand_normalization_removes_fused_tablet_and_status_suffix() -> None:
    assert normalize_arabic_review_brand(
        "\u0632\u064a\u062b\u0631\u0648\u0646 3\u0642\u0631\u0635 \u0633 \u062c\u062f\u064a\u062f"
    ) == "\u0632\u064a\u062b\u0631\u0648\u0646"


def test_review_brand_normalization_does_not_strip_unqualified_brand_suffix() -> None:
    assert normalize_arabic_review_brand("\u0627\u062a\u0648\u0631 \u0633") == "\u0627\u062a\u0648\u0631 \u0633"
    assert normalize_arabic_review_brand("\u0627\u062a\u0648\u0631 \u0633 \u062c\u062f\u064a\u062f") == "\u0627\u062a\u0648\u0631 \u0633"


def test_index_uses_audited_alias_keys_without_cross_target_rows() -> None:
    closol = TargetProduct(
        code="closol-target",
        name="\u0643\u0644\u0648\u0633\u0648\u0644 \u0628\u062e\u0627\u062e \u0645\u0648\u0636\u0639\u064a 50 \u0645\u0644",
        price=10.0,
        discount_percent=0.0,
    )
    adolor = TargetProduct(
        code="adolor-target",
        name="\u0627\u062f\u0648\u0644\u0648\u0631 30 \u0645\u062c\u0645 3 \u0627\u0645\u0628\u0648\u0644",
        price=11.0,
        discount_percent=0.0,
    )

    with (
        patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={
                "rows": [
                    {
                        "en": "CLOSOL 50 ML SPRAY",
                        "ar": "\u0643\u0644\u0648\u0633\u0648\u0644 \u0633\u0628\u0631\u0627\u0649 50\u0645\u0644\u0644\u0649",
                    },
                    {
                        "en": "ADOLOR 30 MG 3 AMP",
                        "ar": "\u0627\u062f\u0648\u0644\u0648\u0631 30\u0645\u062c\u0645 3 \u0627\u0645\u0628\u0648\u0644\u0627\u062a",
                    },
                ]
            },
        ),
        patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ),
        patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={},
        ),
    ):
        index = ExcelTargetBilingualIndex.build([closol, adolor])

    closol_matches = index.identify("CLOSOL 50 ML SPRAY")
    adolor_matches = index.identify("ADOLOR 30 MG 3 AMP")
    assert [match.product.code for match in closol_matches] == ["closol-target"]
    assert [match.product.code for match in adolor_matches] == ["adolor-target"]


def test_approved_alias_precedes_cached_cohere_evidence() -> None:
    product = TargetProduct(
        code="cogicin-target",
        name="\u0643\u0648\u062c\u064a\u0633\u064a\u0646 30 \u0642\u0631\u0635",
        price=10.0,
        discount_percent=0.0,
    )

    with (
        patch(
            "src.core.excel_target.excel_target_identity.load_tawreed_catalog",
            return_value={"rows": []},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.load_dictionary",
            return_value={"by_en": {}},
        ),
        patch(
            "src.core.excel_target.excel_target_identity.lookup_en",
            return_value=[],
        ),
        patch(
            "src.core.excel_target.excel_target_identity.ar_to_en_many_cached_only",
            return_value={product.name: "COGICINE 30 TABS"},
        ),
    ):
        index = ExcelTargetBilingualIndex.build([product])

    matches = index.identify("COGICINE 30 TABS")
    assert len(matches) == 1
    assert matches[0].evidence.kind == "safe_alias"
