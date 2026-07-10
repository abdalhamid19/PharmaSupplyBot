"""Regression tests for BEBELAC LF manual-review candidate limits."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch

from src.core.artifact_run import artifact_run
from src.core.manual_review.manual_review_candidate_store import load_review_candidates
from src.core.manual_review.manual_review_candidates import ReviewCandidateOption
from src.core.matching_types import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown
from src.core.utils.excel import Item
from src.tawreed.order.tawreed_order_summary_build import _save_review_candidates_if_available
from src.ui.manual_review import streamlit_manual_review_page as page


ITEM = Item("30089", "BEBELAC LF MILK", 1)


class BebelacManualReviewCandidateLimitTests(TestCase):
    """Verify saved and displayed manual-review options for BEBELAC LF."""

    def test_saves_configured_number_of_bebelac_candidates(self) -> None:
        decision = MatchDecision(None, _diagnostics(8), "needs review")
        config = SimpleNamespace(manual_review_save_candidate_limit=8)

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "artifacts"
            with artifact_run("order", "wardany", "bebelac_limit", root):
                _save_review_candidates_if_available(decision, ITEM, config)
                loaded = load_review_candidates(root / "order" / "wardany" / "bebelac_limit")

        self.assertEqual(len(loaded["30089::BEBELAC LF MILK"]), 8)

    def test_gui_additional_candidate_input_adds_to_config_default(self) -> None:
        app_config = SimpleNamespace(
            matching=SimpleNamespace(manual_review_display_candidate_limit=5)
        )

        with (
            patch.object(page.st, "caption") as caption,
            patch.object(page.st, "number_input", return_value=3) as number_input,
        ):
            limit = page._candidate_display_limit(app_config)

        self.assertEqual(limit, 8)
        caption.assert_called_once()
        number_input.assert_called_once()

    def test_render_run_candidates_displays_saved_bebelac_extra_options(self) -> None:
        options = _options(8)
        app_config = SimpleNamespace(
            matching=SimpleNamespace(manual_review_display_candidate_limit=5)
        )

        with (
            patch.object(page, "load_review_candidates", return_value={
                "30089::BEBELAC LF MILK": options,
            }),
            patch.object(page, "manual_review_store_or_stop", return_value=object()),
            patch.object(page, "_candidate_display_limit", return_value=8),
            patch.object(page, "_paginate_candidates", side_effect=lambda items: items),
            patch.object(page, "_render_item_card") as render_card,
            patch.object(page.st, "subheader"),
            patch.object(page.st, "checkbox", return_value=False),
        ):
            page.render_run_candidates(Path("run"), app_config)

        rendered_options = render_card.call_args.args[2]
        self.assertEqual(len(rendered_options), 8)
        self.assertEqual(rendered_options[0].name_en, "BEBELAC LF MILK OPTION 1")


def _diagnostics(count: int) -> list[CandidateMatchDiagnostic]:
    return [_diagnostic(i) for i in range(1, count + 1)]


def _diagnostic(index: int) -> CandidateMatchDiagnostic:
    name = f"BEBELAC LF MILK OPTION {index}"
    return CandidateMatchDiagnostic(
        query=ITEM.name, row_index=index, score=20.0 - index,
        sort_key=(20.0 - index,), accepted=False, accepted_reason="",
        rejection_reason="manual review", candidate={
            "storeProductId": f"bebelac-{index}",
            "productNameEn": name,
            "productName": f"بيبيلاك ال اف {index}",
            "availableQuantity": index,
            "salePrice": 100 + index,
        },
        breakdown=MatchScoreBreakdown(0.5, 0.5, 0.0, 0.0, 1.0, 0, 0, 0, 20.0 - index),
    )


def _options(count: int) -> list[ReviewCandidateOption]:
    return [
        ReviewCandidateOption(
            store_product_id=f"bebelac-{i}", name_en=f"BEBELAC LF MILK OPTION {i}",
            name_ar=f"بيبيلاك ال اف {i}", supplier="supplier", available_quantity=i,
            price=100.0 + i, score=20.0 - i, rejection_reason="review", orderable=True,
        )
        for i in range(1, count + 1)
    ]


if __name__ == "__main__":
    main()
