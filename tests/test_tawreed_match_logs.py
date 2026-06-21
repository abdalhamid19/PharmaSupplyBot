import unittest
from unittest.mock import patch

from src.core.matching_models import (
    CandidateMatchDiagnostic,
    MatchDecision,
    MatchScoreBreakdown,
    SearchMatch,
)
from src.core.utils.excel import Item
from src.tawreed.tawreed_match_logs import (
    MAX_DETAILED_MATCH_CANDIDATES,
    OrderResultSummary,
    append_order_result_summary,
    match_log_csv_rows,
    write_match_log,
    should_write_detailed_match_log,
)
from src.tawreed.tawreed_match_only_rows import match_only_summary_rows
from src.tawreed.tawreed_match_only_summary import append_match_only_summary


class TawreedMatchLogsTests(unittest.TestCase):
    def test_append_order_result_summary_writes_structured_status_row(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        summary = OrderResultSummary(
            status="matched-but-unavailable",
            reason="Matched product is unavailable.",
            ordered_total_qty=2,
            matched_product_english_name="Panadol Extra 24 Tabs",
            matched_product_english_name_source="site",
            matched_product_arabic_name="بنادول اكسترا 24 قرص",
            matched_query="Panadol Extra",
            selected_discount_percent="35%",
            selected_store_name="Abu Amira",
            searched_queries_count=2,
            searched_queries="Panadol Extra | Panadol",
        )

        with (
            patch("src.tawreed.tawreed_match_logs.append_csv_artifact") as append_csv,
            patch("src.tawreed.tawreed_match_logs.append_xlsx_artifact") as append_xlsx,
        ):
            append_order_result_summary("wardany", item, summary)

        expected_row = {
            "item_code": "123",
            "item_name": "Panadol Extra",
            "item_qty": 2,
            "ordered_total_qty": 2,
            "status": "matched-but-unavailable",
            "reason": "Matched product is unavailable.",
            "matched_product_english_name": "Panadol Extra 24 Tabs",
            "matched_product_english_name_source": "site",
            "matched_product_arabic_name": "بنادول اكسترا 24 قرص",
            "matched_query": "Panadol Extra",
            "selected_discount_percent": "35%",
            "selected_store_name": "Abu Amira",
            "searched_queries_count": 2,
            "searched_queries": "Panadol Extra | Panadol",
            "elapsed_seconds": 0.0,
            "match_elapsed_seconds": 0.0,
            "api_context_init_seconds": 0.0,
            "api_search_seconds": 0.0,
            "dom_wait_seconds": 0.0,
            "dialog_close_seconds": 0.0,
            "manual_review_lookup_seconds": 0.0,
            "match_decision_seconds": 0.0,
            "add_to_cart_seconds": 0.0,
            "artifact_write_seconds": 0.0,
            "summary_build_seconds": 0.0,
        }
        append_csv.assert_called_once_with(
            "wardany", "order_result_summary", [expected_row]
        )
        append_xlsx.assert_called_once_with(
            "wardany", "order_result_summary", [expected_row]
        )

    def test_match_only_summary_rows_include_api_payload_and_scores(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        candidate = {
            "productId": 99,
            "storeProductId": 1001,
            "productNameEn": "Panadol Extra 24 Tabs",
            "productName": "بنادول اكسترا 24 قرص",
            "availableQuantity": 12,
            "discountPercent": 31,
            "salePrice": 20.5,
        }
        decision = _accepted_decision(candidate)
        summary = OrderResultSummary(status="matched-only", reason="match only")

        rows = match_only_summary_rows(item, summary, decision)

        self.assertEqual(rows[0]["api_productId"], 99)
        self.assertEqual(rows[0]["api_storeProductId"], 1001)
        self.assertEqual(rows[0]["api_discountPercent"], 31)
        self.assertEqual(rows[0]["candidate_source"], "site_api")
        self.assertTrue(rows[0]["is_best_match"])
        raw_candidate_json = str(rows[0]["api_raw_candidate_json"])
        self.assertIn("Panadol Extra", raw_candidate_json)

    def test_append_match_only_summary_writes_independent_csv(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        summary = OrderResultSummary(status="matched-only", reason="match only")

        with patch(
            "src.tawreed.tawreed_match_only_summary.append_csv_artifact"
        ) as append_csv:
            append_match_only_summary("wardany", item, summary, None, "worker_0")

        append_csv.assert_called_once()
        self.assertEqual(append_csv.call_args.args[1], "match_only_summary")
        self.assertEqual(append_csv.call_args.kwargs["label_suffix"], "worker_0")

    def test_should_write_detailed_match_log_skips_clean_high_overlap_accept(
        self,
    ) -> None:
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
                    breakdown=MatchScoreBreakdown(
                        0.95, 1.0, 0.0, 2.0, 1.0, 0.0, 0.0, 0.0, 22.5
                    ),
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

    def test_write_match_log_uses_unified_matching_trace_csv(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        decision = MatchDecision(
            best_match=None,
            diagnostics=[],
            final_reason="No search candidates were returned.",
        )
        bot = type("Bot", (), {"profile_key": "wardany"})()

        with (
            patch("src.tawreed.tawreed_match_logs.write_text_artifact"),
            patch("src.tawreed.tawreed_match_logs.append_text_artifact"),
            patch("src.tawreed.tawreed_match_logs.append_csv_artifact") as append_csv,
        ):
            write_match_log(bot, item, decision)

        self.assertEqual(append_csv.call_args.args[1], "matching_trace")

    def test_match_log_csv_rows_are_bounded_for_large_candidate_sets(self) -> None:
        item = Item(code="123", name="Panadol Extra", qty=2)
        decision = MatchDecision(
            best_match=None,
            diagnostics=[
                CandidateMatchDiagnostic(
                    "Panadol Extra",
                    index,
                    float(index),
                    (float(index),),
                    False,
                    "",
                    "rejected",
                    MatchScoreBreakdown(0, 0, 0, 0, 0, 0, 0, 0, float(index)),
                    {"productNameEn": f"Candidate {index}"},
                )
                for index in range(MAX_DETAILED_MATCH_CANDIDATES + 10)
            ],
            final_reason="No accepted candidate",
        )

        rows = match_log_csv_rows(item, decision)

        self.assertEqual(len(rows), MAX_DETAILED_MATCH_CANDIDATES)
        self.assertEqual(rows[0]["product_name_en"], "Candidate 34")


def _accepted_decision(candidate: dict[str, object]) -> MatchDecision:
    """Return an accepted decision fixture for summary-row tests."""
    return MatchDecision(
        best_match=SearchMatch("Panadol Extra", 0, 22.5, candidate),
        diagnostics=[
            CandidateMatchDiagnostic(
                "Panadol Extra",
                0,
                22.5,
                (22.5, 1, 1.0, 1, 10, 10),
                True,
                "high_token_overlap",
                "",
                MatchScoreBreakdown(0.95, 1.0, 0.0, 2.0, 1.0, 0.0, 0.0, 0.0, 22.5),
                candidate,
            )
        ],
        final_reason="Accepted",
    )


if __name__ == "__main__":
    unittest.main()
