import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.tawreed_products_flow import (
    _disabled_cart_reason,
    _decisive_match,
    is_no_results_row,
    _should_stop_after_no_results,
    _table_has_no_results,
    fill_add_to_cart_dialog,
    open_add_to_cart_for_match,
    open_store_cart_dialog,
    open_stores_dialog,
    search_products,
    store_discount_percent,
    store_name,
)
from src.excel import Item
from src.matching_models import CandidateMatchDiagnostic, MatchDecision, MatchScoreBreakdown, SearchMatch


class _FakeExpectResponse:
    def __init__(self, response=None, enter_error=None, exit_error=None):
        self.value = response
        self._enter_error = enter_error
        self._exit_error = exit_error

    def __enter__(self):
        if self._enter_error:
            raise self._enter_error
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._exit_error:
            raise self._exit_error
        return False


class _FakeSearchLocator:
    def __init__(self):
        self.click_count = 0
        self.fills = []
        self.presses = []

    @property
    def first(self):
        return self

    def click(self):
        self.click_count += 1

    def fill(self, value):
        self.fills.append(value)

    def press(self, key):
        self.presses.append(key)


class _FakePage:
    def __init__(self, search_locator=None, expect_response=None):
        self._search_locator = search_locator or _FakeSearchLocator()
        self._expect_response = expect_response or _FakeExpectResponse()
        self.load_states = []

    def locator(self, selector):
        return self._search_locator

    def expect_response(self, predicate, timeout):
        return self._expect_response

    def wait_for_load_state(self, state, timeout=None):
        self.load_states.append((state, timeout))


class _FakeDialog:
    def __init__(self, quantity_input, wait_error=None):
        self._quantity_input = quantity_input
        self._wait_error = wait_error

    def locator(self, selector):
        return self._quantity_input

    def wait_for(self, state=None, timeout=None):
        if self._wait_error:
            raise self._wait_error
        return None


class _FakeQuantityInput:
    @property
    def first(self):
        return self


class _FakeButton:
    def __init__(self):
        self.click_count = 0

    def click(self):
        self.click_count += 1


class _FakeFooterButtons:
    def __init__(self):
        self.last = _FakeButton()


class _FakeCartButtons:
    def __init__(self, count):
        self.count = count
        self.clicked_index = None

    def nth(self, index):
        self.clicked_index = index
        return _FakeButton()


class _FakeRows:
    def __init__(self, rows):
        self._rows = rows

    def count(self):
        return len(self._rows)

    def nth(self, index):
        return self._rows[index]


class _FakeTextLocator:
    def __init__(self, text):
        self._text = text

    @property
    def first(self):
        return self

    def inner_text(self):
        return self._text


class _FakeCellLocator:
    def __init__(self, row):
        self._row = row

    @property
    def first(self):
        return self

    def locator(self, selector):
        return _FakeTextLocator(self._row.name_block)


class _FakeRow:
    def __init__(self, name_block, suppliers="1", cart="0", row_text="row text", red_message=""):
        self.name_block = name_block
        self.suppliers = suppliers
        self.cart = cart
        self.row_text = row_text
        self.red_message = red_message

    def locator(self, selector):
        if selector == "td":
            return _FakeCellLocator(self)
        if selector == "button:has(.pi-building) .p-badge":
            return _FakeTextLocator(self.suppliers)
        if selector == "button:has(.pi-shopping-cart) .p-badge":
            return _FakeTextLocator(self.cart)
        if selector == "div[style*='color: red']":
            return _FakeTextLocator(self.red_message)
        raise AssertionError(f"unexpected selector: {selector}")

    def inner_text(self):
        return self.row_text


class TawreedProductsFlowTests(unittest.TestCase):
    def test_decisive_match_accepts_high_overlap_first_query(self):
        item = Item(code="1", name="HAIR PLUS BACK 5% TOPICAL FOAM 100 ML", qty=1)
        candidate = {"productNameEn": "HAIR PLUS BACK TOPICAL FOAM ML 5 100"}
        decision = MatchDecision(
            best_match=SearchMatch(query=item.name, row_index=0, score=19.3, data=candidate),
            diagnostics=[
                CandidateMatchDiagnostic(
                    query=item.name,
                    row_index=0,
                    score=19.3,
                    sort_key=(19.3, 0, 1.0, 2, 20, 20),
                    accepted=True,
                    accepted_reason="high_token_overlap",
                    rejection_reason="",
                    breakdown=MatchScoreBreakdown(0.86, 1.0, 1.0, 0.0, 1.0, 19.3),
                    candidate=candidate,
                )
            ],
            final_reason="Accepted best candidate because high_token_overlap.",
        )

        self.assertFalse(_decisive_match(item, item.name, decision, 0, 8))
        self.assertFalse(_decisive_match(item, item.name, decision, 1, 8))
        self.assertTrue(_decisive_match(item, item.name, decision, 2, 8))

    def test_decisive_match_rejects_weaker_non_exact_first_query(self):
        item = Item(code="1", name="OPTIPRED 10MG/ML EYE DROPS 5 ML", qty=1)
        candidate = {"productNameEn": "OPTIPRED EYE DROPS ML 10 5"}
        decision = MatchDecision(
            best_match=SearchMatch(query=item.name, row_index=0, score=17.6, data=candidate),
            diagnostics=[
                CandidateMatchDiagnostic(
                    query=item.name,
                    row_index=0,
                    score=17.6,
                    sort_key=(17.6, 0, 0.875, 2, 26, 26),
                    accepted=True,
                    accepted_reason="high_token_overlap",
                    rejection_reason="",
                    breakdown=MatchScoreBreakdown(0.72, 0.875, 1.0, 0.0, 1.0, 17.6),
                    candidate=candidate,
                )
            ],
            final_reason="Accepted best candidate because high_token_overlap.",
        )

        self.assertFalse(_decisive_match(item, item.name, decision, 2, 8))

    def test_search_products_returns_dom_results_when_rows_appear(self):
        page = _FakePage()
        rows = _FakeRows([_FakeRow("دونيبيزيل 10 مجم اقراص", suppliers="1", cart="0")])
        bot = SimpleNamespace(
            selectors=SimpleNamespace(item_search_input="#search"),
            config=SimpleNamespace(runtime=SimpleNamespace(timeout_ms=5000)),
        )

        with (
            patch("src.tawreed_products_flow.close_visible_dialogs") as close_dialogs,
            patch("src.tawreed_products_flow.wait_for_product_rows") as wait_rows,
            patch("src.tawreed_products_flow.visible_product_rows", return_value=rows),
        ):
            results = search_products(bot, page, "DONEPEZIL")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["productNameEn"], "DONEPEZIL 10")
        close_dialogs.assert_called_once_with(page)
        wait_rows.assert_called_once_with(page)
        self.assertEqual(page._search_locator.presses, ["Enter"])

    def test_search_products_returns_empty_when_table_has_no_results(self):
        page = _FakePage()
        bot = SimpleNamespace(
            selectors=SimpleNamespace(item_search_input="#search"),
            config=SimpleNamespace(runtime=SimpleNamespace(timeout_ms=5000)),
        )

        with (
            patch("src.tawreed_products_flow.close_visible_dialogs"),
            patch("src.tawreed_products_flow.wait_for_product_rows"),
            patch(
                "src.tawreed_products_flow.visible_product_rows",
                return_value=_FakeRows([_FakeRow("ignored", row_text="No results found")]),
            ),
        ):
            results = search_products(bot, page, "DONEPEZIL")

        self.assertEqual(results, [])

    def test_open_stores_dialog_uses_visible_dialog_rows_without_response(self):
        bot = SimpleNamespace(config=SimpleNamespace(runtime=SimpleNamespace(timeout_ms=5000)))
        page = _FakePage(expect_response=_FakeExpectResponse(exit_error=RuntimeError("timeout")))
        row = object()

        with (
            patch("src.tawreed_products_flow.stores_button") as stores_button,
            patch("src.tawreed_products_flow._stores_dialog_visible", return_value=True),
            patch("src.tawreed_products_flow._stores_from_dialog_rows", return_value=[{}, {}]) as dialog_rows,
        ):
            stores_button.return_value.click.return_value = None
            stores = open_stores_dialog(bot, page, row)

        self.assertEqual(stores, [{}, {}])
        dialog_rows.assert_called_once_with(page, bot)

    def test_open_store_cart_dialog_records_selected_store_details(self):
        store_rows = [
            {"availableQuantity": 1, "supplierName": "Old Store", "discountPercent": 10},
            {"availableQuantity": 5, "storeName": "Abu Amira", "discount": 0.35},
        ]
        cart_buttons = _FakeCartButtons(count=2)
        dialog = object()
        bot = SimpleNamespace(
            config=SimpleNamespace(
                runtime=SimpleNamespace(timeout_ms=5000),
                warehouse_strategy={"mode": "max_available"},
            ),
            skip_item_exception=RuntimeError,
            last_selected_discount_percent="",
            last_selected_store_name="",
        )

        with (
            patch("src.tawreed_products_flow.open_stores_dialog", return_value=store_rows),
            patch("src.tawreed_products_flow.visible_dialog", return_value=dialog),
            patch("src.tawreed_products_flow.store_dialog_cart_buttons", return_value=cart_buttons),
        ):
            open_store_cart_dialog(bot, object(), object())

        self.assertEqual(bot.last_selected_discount_percent, "35%")
        self.assertEqual(bot.last_selected_store_name, "Abu Amira")
        self.assertEqual(cart_buttons.clicked_index, 1)

    def test_open_add_to_cart_prefers_store_dialog_when_supplier_details_exist(self):
        bot = SimpleNamespace(skip_item_exception=RuntimeError)
        match = SearchMatch(
            query="Panadol",
            row_index=0,
            score=10,
            data={"productsCount": 1, "availableQuantity": 1},
        )

        with (
            patch("src.tawreed_products_flow.open_store_cart_dialog") as open_dialog,
            patch("src.tawreed_products_flow.click_single_store_cart") as click_single,
        ):
            open_add_to_cart_for_match(bot, object(), object(), Item("1", "Panadol", 1), match)

        open_dialog.assert_called_once()
        click_single.assert_not_called()

    def test_open_add_to_cart_falls_back_to_direct_cart_when_store_dialog_fails(self):
        bot = SimpleNamespace(skip_item_exception=RuntimeError)
        match = SearchMatch(
            query="Panadol",
            row_index=0,
            score=10,
            data={"productsCount": 1, "availableQuantity": 1},
        )

        with (
            patch(
                "src.tawreed_products_flow.open_store_cart_dialog",
                side_effect=ValueError("dialog failed"),
            ),
            patch("src.tawreed_products_flow._row_cart_button_enabled", return_value=True),
            patch("src.tawreed_products_flow.close_visible_dialogs") as close_dialogs,
            patch("src.tawreed_products_flow.click_single_store_cart") as click_single,
        ):
            open_add_to_cart_for_match(bot, object(), object(), Item("1", "Panadol", 1), match)

        close_dialogs.assert_called_once()
        click_single.assert_called_once()

    def test_store_summary_extracts_nested_payload_fields(self):
        store = {
            "supplier": {"name": "Abu Amira"},
            "discount": {"percentage": "35 %"},
        }

        self.assertEqual(store_name(store), "Abu Amira")
        self.assertEqual(store_discount_percent(store), "35%")

    def test_fill_add_to_cart_dialog_cleans_up_when_dialog_stays_visible(self):
        quantity_input = _FakeQuantityInput()
        footer_buttons = _FakeFooterButtons()
        dialog = _FakeDialog(quantity_input, wait_error=RuntimeError("still visible"))
        bot = SimpleNamespace(config=SimpleNamespace(runtime=SimpleNamespace(timeout_ms=5000)))
        page = _FakePage()

        with (
            patch("src.tawreed_products_flow.visible_dialog", return_value=dialog),
            patch("src.tawreed_products_flow.dialog_footer_buttons", return_value=footer_buttons),
            patch("src.tawreed_products_flow.bounded_requested_quantity", return_value=2),
            patch("src.tawreed_products_flow.fill_quantity_input") as fill_quantity,
            patch("src.tawreed_products_flow.close_visible_dialogs") as close_dialogs,
            patch("src.tawreed_products_flow._wait_for_dialog_to_clear") as wait_clear,
        ):
            fill_add_to_cart_dialog(bot, page, 4)

        fill_quantity.assert_called_once_with(quantity_input, 2)
        self.assertEqual(footer_buttons.last.click_count, 1)
        close_dialogs.assert_called_once_with(page)
        wait_clear.assert_called_once_with(page)

    def test_disabled_cart_reason_uses_visible_unavailable_message(self):
        row = _FakeRow(
            "دوليبران 1 جم 8 كيس",
            suppliers="0",
            cart="0",
            red_message="المنتج غير متوفر",
        )

        reason = _disabled_cart_reason(row, "DOLIPRANE 8 TABLETS")

        self.assertIn("المنتج غير متوفر", reason)

    def test_should_stop_after_first_empty_query(self):
        queries = [
            "QUINSTIBOWL 5MG 20F.C TABS",
            "QUINSTIBOWL 5 MG 20 F C TABS",
            "QUINSTIBOWL 5MG 20F.C",
        ]

        self.assertFalse(_should_stop_after_no_results(queries, 0, []))
        self.assertFalse(_should_stop_after_no_results(queries, 1, []))
        self.assertTrue(_should_stop_after_no_results(queries, 2, []))
        self.assertFalse(_should_stop_after_no_results(queries, 1, [{}]))

    def test_table_has_no_results_detects_single_empty_row(self):
        page = _FakePage()
        rows = _FakeRows([_FakeRow("ignored", row_text="No results found")])

        with patch("src.tawreed_products_flow.visible_product_rows", return_value=rows):
            self.assertTrue(_table_has_no_results(page))

    def test_is_no_results_row_accepts_arabic_text(self):
        row = _FakeRow("ignored", row_text="لا يوجد نتائج")
        self.assertTrue(is_no_results_row(row))


if __name__ == "__main__":
    unittest.main()
