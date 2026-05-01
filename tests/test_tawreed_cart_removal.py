import unittest
from unittest.mock import patch

from src.cart_removal_items import CartRemovalItem
from src.tawreed_cart_removal import (
    CartRemovalSelectors,
    remove_items_from_cart,
    remove_matching_cart_rows,
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
    def __init__(self, text):
        self.text = text
        self.deleted = False

    def inner_text(self, timeout=None):
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
            _FakeRow("Supplier A 47273 DEVAROL"),
            _FakeRow("Supplier B 47273 DEVAROL"),
            _FakeRow("Supplier C PANADOL"),
        ]
        page = _FakePage(rows)
        selectors = CartRemovalSelectors("rows", "delete", "confirm")

        with patch("src.tawreed_cart_removal.confirm_delete_if_needed"):
            removed_count = remove_matching_cart_rows(
                page,
                CartRemovalItem(code="47273", name="DEVAROL"),
                selectors,
            )

        self.assertEqual(removed_count, 2)
        self.assertEqual([row.deleted for row in rows], [True, True, False])

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

        with patch("src.tawreed_cart_removal.append_cart_removal_summary") as append_summary:
            remove_items_from_cart(bot, page, [CartRemovalItem(code="47273", name="DEVAROL")])

        summary = append_summary.call_args.args[2]
        self.assertEqual(summary.removed_count, 0)
        self.assertEqual(summary.status, "not-found")


if __name__ == "__main__":
    unittest.main()
