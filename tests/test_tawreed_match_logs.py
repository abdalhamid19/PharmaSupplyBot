import unittest

from src.excel import Item
from src.matching_models import MatchDecision, SearchMatch
from src.tawreed_match_logs import match_summary_rows


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


if __name__ == "__main__":
    unittest.main()
