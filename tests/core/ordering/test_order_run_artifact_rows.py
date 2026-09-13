from __future__ import annotations

from src.core.database.order_runs_rows import run_item_row
from src.core.matching_types import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
)
from src.core.ordering.order_run_artifact_rows import order_item_summary_row
from src.core.utils.excel import Item
from src.tawreed.matching.tawreed_match_logs import OrderResultSummary


def test_not_orderable_artifact_keeps_recognized_name_without_store_id() -> None:
    item = Item("92558", "LIMITLESS MILGA MAX 30 TABS", 17)
    decision = MatchDecision(
        best_match=None,
        diagnostics=[
            CandidateMatchDiagnostic(
                query=item.name,
                row_index=0,
                score=20.5,
                sort_key=(20.5, 0, 0, 0, 0, 0),
                accepted=False,
                accepted_reason="",
                rejection_reason="Candidate missing orderable storeProductId",
                breakdown=MatchScoreBreakdown(1, 1, 1, 1, 1, 0, 0, 0, 20.5),
                candidate={
                    "productNameEn": "LIMITLESS MILGA MAX 30 TABS",
                    "productName": "ليمتلس ميلجا ماكس 30 اقراص",
                },
            ),
            CandidateMatchDiagnostic(
                query=item.name,
                row_index=1,
                score=20.615384615384617,
                sort_key=(20.615384615384617, 0, 0, 0, 0, 1),
                accepted=False,
                accepted_reason="",
                rejection_reason=(
                    "Product identity conflict: requested LIMITLESS MILGA MAX "
                    "but candidate is LIMITLESS MAN MAX"
                ),
                breakdown=MatchScoreBreakdown(
                    1, 1, 1, 1, 1, 0, 0, 0, 20.615384615384617
                ),
                candidate={
                    "storeProductId": "2940276",
                    "productNameEn": "LIMITLESS MAN MAX 30 TABS",
                    "productName": "ليمتلس مان 30 اقراص س جديد",
                },
            ),
        ],
        final_reason="No decisive match found",
    )
    summary = OrderResultSummary(
        status="not-orderable",
        reason="No decisive match found",
        ordered_total_qty=0,
    )

    row = order_item_summary_row(item, summary, decision)

    assert row["matched_product_name_en"] == "LIMITLESS MILGA MAX 30 TABS"
    assert row["matched_product_name_ar"] == "ليمتلس ميلجا ماكس 30 اقراص"
    assert row["matched_store_product_id"] == ""
    assert row["matched"] is False
    assert row["deterministic_match_found"] is False
    assert row["manual_review_required"] is True

    persisted_row = run_item_row("wardany/20260913_1516", row)

    assert persisted_row["matched_name_en"] == "LIMITLESS MILGA MAX 30 TABS"
    assert persisted_row["matched_name_ar"] == "ليمتلس ميلجا ماكس 30 اقراص"
    assert persisted_row["winner_store_product_id"] is None
