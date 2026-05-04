import unittest
from unittest.mock import patch

from src.core.cart_removal_items import CartRemovalItem
from src.tawreed.tawreed_cart_removal import (
    CartRemovalSelectors,
    CartRemovalTarget,
    remove_items_from_cart,
    remove_matching_cart_rows,
    resolve_cart_removal_targets,
)


class _FakeButton:
    def __init__(self, row):
        self.row = row

    @property
    def first(self):
        return self

    def click(self, timeout=None):
        self.row.deleted = True


class _FakeRow:
    def __init__(self, text, text_error=None):
        self.text = text
        self.text_error = text_error
        self.deleted = False

    def inner_text(self, timeout=None):
        if self.text_error:
            raise self.text_error
        return self.text

    def locator(self, selector):
        return _FakeButton(self)


class _FakeRows:
    def __init__(self, rows):
        self.rows = rows

    def count(self):
        return len([row for row in self.rows if not row.deleted])

    def nth(self, index):
        return [row for row in self.rows if not row.deleted][index]

    @property
    def first(self):
        return self.nth(0)


class _FakePage:
    def __init__(self, rows):
        self.rows = _FakeRows(rows)

    def locator(self, selector):
        return self.rows


class TawreedCartRemovalTests(unittest.TestCase):
    def test_remove_matching_cart_rows_deletes_all_matching_suppliers(self) -> None:
        rows = [
            _FakeRow("Supplier A DEVAROL"),
            _FakeRow("Supplier B DEVAROL"),
            _FakeRow("Supplier C PANADOL"),
        ]
        page = _FakePage(rows)
        selectors = CartRemovalSelectors("rows", "delete", "confirm")

        with patch("src.tawreed.tawreed_cart_removal.confirm_delete_if_needed"):
            removed_count = remove_matching_cart_rows(
                page,
                CartRemovalTarget(
                    item=CartRemovalItem(code="47273", name="DEVAROL"),
                    names=["DEVAROL", "ديفارول"],
                ),
                selectors,
            )

        self.assertEqual(removed_count, 2)
        self.assertEqual([row.deleted for row in rows], [True, True, False])

    def test_remove_matching_cart_rows_counts_row_removed_despite_click_error(self) -> None:
        rows = [_FakeRow("Supplier A DEVAROL")]
        page = _FakePage(rows)
        selectors = CartRemovalSelectors("rows", "delete", "confirm")
        target = CartRemovalTarget(
            item=CartRemovalItem(code="47273", name="DEVAROL"),
            names=["DEVAROL"],
        )

        def detach_row_after_click_error(delete_button):
            rows[0].deleted = True
            raise RuntimeError("element detached")

        with patch("src.tawreed.tawreed_cart_removal.click_cart_delete_button", side_effect=detach_row_after_click_error):
            removed_count = remove_matching_cart_rows(page, target, selectors)

        self.assertEqual(removed_count, 1)

    def test_remove_matching_cart_rows_skips_unreadable_virtual_rows(self) -> None:
        rows = [
            _FakeRow("virtual row", text_error=TimeoutError("not rendered")),
            _FakeRow("Supplier A DEVAROL"),
        ]
        page = _FakePage(rows)
        selectors = CartRemovalSelectors("rows", "delete", "confirm")
        target = CartRemovalTarget(
            item=CartRemovalItem(code="47273", name="DEVAROL"),
            names=["DEVAROL"],
        )

        with patch("src.tawreed.tawreed_cart_removal.confirm_delete_if_needed"):
            removed_count = remove_matching_cart_rows(page, target, selectors)

        self.assertEqual(removed_count, 1)

    def test_remove_items_from_cart_writes_not_found_summary(self) -> None:
        bot = type(
            "Bot",
            (),
            {
                "profile_key": "wardany",
                "selectors": type(
                    "Selectors",
                    (),
                    {
                        "cart_rows": "rows",
                        "cart_delete_button": "delete",
                        "cart_confirm_delete_button": "confirm",
                    },
                )(),
            },
        )()
        page = _FakePage([_FakeRow("Supplier C PANADOL")])
        target = CartRemovalTarget(
            item=CartRemovalItem(code="47273", name="DEVAROL"),
            names=["DEVAROL", "ديفارول"],
        )

        with patch("src.tawreed.tawreed_cart_removal.append_cart_removal_summary") as append_summary:
            remove_items_from_cart(bot, page, [target])

        summary = append_summary.call_args.args[2]
        self.assertEqual(summary.removed_count, 0)
        self.assertEqual(summary.status, "not-found")

    def test_resolve_cart_removal_targets_adds_tawreed_arabic_name(self) -> None:
        bot = type("Bot", (), {"profile_key": "wardany"})()
        item = CartRemovalItem(code="47273", name="DEVAROL-S-200.000 I.U 1 AMP")
        match = type(
            "Match",
            (),
            {
                "data": {
                    "productName": "ديفارول اس 200000 وحده 1 امبول",
                    "productNameEn": "DEVAROL S 200000 IU 1 AMP",
                }
            },
        )()

        with patch("src.tawreed.tawreed_cart_removal.require_product_match", return_value=(match, "DEVAROL")):
            targets = resolve_cart_removal_targets(bot, object(), [item])

        self.assertEqual(targets[0].item, item)
        self.assertIn("ديفارول اس 200000 وحده 1 امبول", targets[0].names)

    def test_resolve_cart_removal_targets_prints_arabic_failures_safely(self) -> None:
        bot = type("Bot", (), {"profile_key": "wardany"})()
        item = CartRemovalItem(code="91976", name="عسل حريمي")

        with (
            patch("src.tawreed.tawreed_cart_removal.require_product_match", side_effect=RuntimeError("لا يوجد")),
            patch("builtins.print") as print_call,
        ):
            targets = resolve_cart_removal_targets(bot, object(), [item])

        self.assertEqual(targets[0].names, [item.name])
        printed_text = print_call.call_args.args[0]
        self.assertIn("??? ?????", printed_text)


if __name__ == "__main__":
    unittest.main()
