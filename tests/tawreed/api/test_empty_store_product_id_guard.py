"""Guard: empty storeProductId must never crash the API order run."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.core.matching_types import MatchDecision, SearchMatch
from src.core.utils.excel import Item
from src.tawreed.api.tawreed_api_flow_cart import _add_single_item_to_cart
from src.tawreed.api.tawreed_api_flow_matching import _require_orderable_api_match
from src.tawreed.api.tawreed_api_payloads import body_with_match
from src.tawreed.order.tawreed_order_placement import _SkipItem


class EmptyStoreProductIdGuardTests(unittest.TestCase):
    """Reproduce and lock the int('') crash from add-to-cart payloads."""

    def test_body_with_match_rejects_empty_store_product_id(self) -> None:
        match = SimpleNamespace(data={"productNameEn": "HALOPERIDOL RETARD 50 MG"})
        with self.assertRaises(ValueError) as raised:
            body_with_match({}, match, 1)
        self.assertIn("storeProductId", str(raised.exception))

    def test_body_with_match_accepts_valid_store_product_id(self) -> None:
        match = SimpleNamespace(data={"storeProductId": "2288836.0"})
        payload = body_with_match({}, match, 2)
        self.assertEqual(payload["data"]["storeProductId"], 2288836)
        self.assertEqual(payload["data"]["quantity"], 2)

    def test_require_orderable_api_match_skips_without_store_id(self) -> None:
        bot = SimpleNamespace(skip_item_exception=_SkipItem)
        match = SearchMatch(
            query="HALOPERIDOL RETARD 1AMP",
            row_index=0,
            score=999.0,
            data={"productNameEn": "HALOPERIDOL RETARD 50 MG / ML I.M.AMP."},
        )
        with self.assertRaises(_SkipItem) as raised:
            _require_orderable_api_match(
                bot, Item(code="29244", name="HALOPERIDOL RETARD 1AMP", qty=1), match
            )
        self.assertIn("not orderable", str(raised.exception).lower())
        self.assertIn("storeproductid", str(raised.exception).lower())

    def test_require_orderable_api_match_allows_orderable_row(self) -> None:
        bot = SimpleNamespace(skip_item_exception=_SkipItem)
        match = SearchMatch(
            query="CAL MAG 30TAB",
            row_index=0,
            score=20.0,
            data={
                "productNameEn": "CAL MAG 30 F.C. TABLETS",
                "storeProductId": "2288836",
            },
        )
        returned = _require_orderable_api_match(
            bot, Item(code="74096", name="CAL MAG 30TAB", qty=1), match
        )
        self.assertIs(returned, match)

    def test_add_single_item_to_cart_skips_missing_store_id(self) -> None:
        bot = SimpleNamespace(
            skip_item_exception=_SkipItem,
            last_ordered_total_qty=0,
        )
        api = MagicMock()
        match = SearchMatch(
            query="x",
            row_index=0,
            score=1.0,
            data={"productNameEn": "X", "storeProductId": ""},
        )
        with self.assertRaises(_SkipItem):
            _add_single_item_to_cart(
                bot,
                api,
                match,
                Item(code="1", name="X", qty=1),
                record_timing=lambda *_a, **_k: None,
            )
        api.add_to_cart.assert_not_called()

    def test_manual_review_not_orderable_prefix_is_detected(self) -> None:
        from src.tawreed.api.tawreed_api_flow_matching import _is_saved_manual_review_match

        decision = MatchDecision(
            best_match=SearchMatch(
                query="q",
                row_index=0,
                score=999.0,
                data={"productNameEn": "P"},
            ),
            diagnostics=[],
            final_reason="Approved by saved manual review (Name match, not orderable).",
        )
        self.assertTrue(_is_saved_manual_review_match(decision))


if __name__ == "__main__":
    unittest.main()
