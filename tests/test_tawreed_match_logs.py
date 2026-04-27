import unittest
from unittest.mock import patch

from src.excel import Item
from src.matching_models import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown, SearchMatch
from src.tawreed_match_logs import (
    OrderItemSummary,
    append_order_result_summary,
    match_summary_rows,
    should_write_detailed_match_log,
)


class TawreedMatchLogsTests(unittest.TestCase):
    def test_match_summary_rows_for_accepted_item(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        decision = MatchDecision(
            best_match=SearchMatch(
                query="Panadol Extra",
                row_index=0,
                score=22.5,
                data={"productNameEn": "Panadol Extra 24 Tabs", "productName": ""},
            ),
            diagnostics=[],
            final_reason="Accepted",
        )

        rows = match_summary_rows(item, decision)

        self.assertEqual(
            rows,
            [
                {
                    "item_name": "Panadol Extra",
                    "accepted": True,
                    "accepted_product_name": "Panadol Extra 24 Tabs",
                }
            ],
        )

    def test_match_summary_rows_for_rejected_item(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        decision = MatchDecision(best_match=None, diagnostics=[], final_reason="Rejected")

        rows = match_summary_rows(item, decision)

        self.assertEqual(
            rows,
            [
                {
                    "item_name": "Panadol Extra",
                    "accepted": False,
                    "accepted_product_name": "",
                }
            ],
        )

    def test_append_order_result_summary_writes_structured_status_row(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        summary = OrderItemSummary(
            status="matched-but-unavailable",
            reason="Matched product is unavailable.",
            matched_product_name="Panadol Extra 24 Tabs",
            matched_query="Panadol Extra",
            searched_queries_count=2,
            searched_queries="Panadol Extra | Panadol",
        )

        with (
            patch("src.tawreed_match_logs.append_csv_artifact") as append_csv,
        ):
            append_order_result_summary("wardany", item, summary)

        expected_row = {
            "item_code": "123",
            "item_name": "Panadol Extra",
            "item_qty": 2,
            "status": "matched-but-unavailable",
            "reason": "Matched product is unavailable.",
            "matched_product_name": "Panadol Extra 24 Tabs",
            "matched_query": "Panadol Extra",
            "searched_queries_count": 2,
            "searched_queries": "Panadol Extra | Panadol",
            "elapsed_seconds": 0.0,
            "match_elapsed_seconds": 0.0,
        }
        append_csv.assert_called_once_with("wardany", "order_result_summary", [expected_row])

    def test_should_write_detailed_match_log_skips_clean_high_overlap_accept(self) -> None:
        candidate = {"productNameEn": "Panadol Extra 24 Tabs", "productName": ""}
        decision = MatchDecision(
            best_match=SearchMatch(
                query="Panadol Extra",
                row_index=0,
                score=22.5,
                data=candidate,
            ),
            diagnostics=[
                CandidateMatchDiagnostic(
                    query="Panadol Extra",
                    row_index=0,
                    score=22.5,
                    sort_key=(22.5, 1, 1.0, 1, 10, 10),
                    accepted=True,
                    accepted_reason="high_token_overlap",
                    rejection_reason="",
                    breakdown=MatchScoreBreakdown(0.95, 1.0, 0.0, 2.0, 1.0, 22.5),
                    candidate=candidate,
                )
            ],
            final_reason="Accepted",
        )

        self.assertFalse(should_write_detailed_match_log(decision))

    def test_should_write_detailed_match_log_keeps_no_results(self) -> None:
        decision = MatchDecision(
            best_match=None,
            diagnostics=[],
            final_reason="No search candidates were returned.",
        )

        self.assertTrue(should_write_detailed_match_log(decision))


if __name__ == "__main__":
    unittest.main()
