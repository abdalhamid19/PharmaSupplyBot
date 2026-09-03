"""Tests for mapping Tawreed store rows into run_item_stores rows."""

from __future__ import annotations

import unittest

from src.core.database.order_runs_stores import (
    product_dimension_row,
    store_dimension_row,
    store_snapshot_rows,
)

_NOW = "2026-08-30T18:09:00"


def _store(store_id: int, discount: float, qty: int = 10, **extra) -> dict:
    """Return a Tawreed store-details row shaped like the real payload."""
    row = {
        "storeId": store_id,
        "storeName": f"شركه {store_id}",
        "storeProductId": 2900000 + store_id,
        "productId": 2505,
        "productName": "كال ماج 30 اقراص",
        "productNameEn": "CAL MAG 30 F.C. TABLETS",
        "availableQuantity": qty,
        "retailPrice": 147.0,
        "salePrice": round(147.0 * (1 - discount / 100), 2),
        "discountPercent": discount,
        "currency": "ج.م",
        "priority": 10,
    }
    row.update(extra)
    return row


class StoreSnapshotRowsTests(unittest.TestCase):
    """One row per offering store, with the strategy's choice flagged."""

    def _rows(self, stores, selections=None, **kwargs):
        return store_snapshot_rows(
            "wardany/1", "12345::CAL MAG", stores, selections or [], _NOW, **kwargs
        )

    def test_one_row_per_offering_store(self) -> None:
        """This is the whole point: every store, not just the winner."""
        rows = self._rows([_store(1, 21.0), _store(2, 15.0), _store(3, 8.0)])
        self.assertEqual(len(rows), 3)

    def test_price_columns_are_not_swapped(self) -> None:
        """purchase_price is what you pay; public_price is the retail price."""
        row = self._rows([_store(1, 21.0)])[0]
        self.assertAlmostEqual(row["public_price"], 147.0)
        self.assertAlmostEqual(row["purchase_price"], 116.13)
        self.assertLess(row["purchase_price"], row["public_price"])

    def test_discount_matches_the_price_difference(self) -> None:
        """Guards against reading the discount from the wrong field."""
        row = self._rows([_store(1, 21.0)])[0]
        computed = (row["public_price"] - row["purchase_price"]) / row["public_price"]
        self.assertAlmostEqual(computed * 100, row["discount_percent"], places=1)

    def test_rank_by_discount_is_precomputed_descending(self) -> None:
        """Rank inside a finished run never changes, so it is stored once."""
        rows = self._rows([_store(1, 8.0), _store(2, 21.0), _store(3, 15.0)])
        by_store = {row["store_key"]: row["rank_by_discount"] for row in rows}
        self.assertEqual(by_store["storeId:2"], 1)
        self.assertEqual(by_store["storeId:3"], 2)
        self.assertEqual(by_store["storeId:1"], 3)

    def test_winner_is_flagged_from_the_selected_store(self) -> None:
        """is_winner records the strategy's actual choice, not the best discount."""
        stores = [_store(1, 8.0), _store(2, 21.0)]
        rows = self._rows(stores, selections=[(stores[0], 10)])
        winners = [row["store_key"] for row in rows if row["is_winner"]]
        self.assertEqual(winners, ["storeId:1"])

    def test_only_one_winner_even_with_split_quantities(self) -> None:
        """Split orders mark several ordered stores but exactly one winner."""
        stores = [_store(1, 21.0), _store(2, 15.0)]
        rows = self._rows(stores, selections=[(stores[0], 6), (stores[1], 4)])
        self.assertEqual(sum(row["is_winner"] for row in rows), 1)
        self.assertEqual(sorted(row["ordered_qty"] for row in rows), [4, 6])

    def test_zero_quantity_choice_is_still_the_match_only_winner(self) -> None:
        """Match-only selects a store without creating a false order quantity."""
        stores = [_store(1, 21.0), _store(2, 15.0)]
        rows = self._rows(stores, selections=[(stores[1], 0)])
        winner = next(row for row in rows if row["is_winner"])
        self.assertEqual(winner["store_key"], "storeId:2")
        self.assertEqual(winner["ordered_qty"], 0)

    def test_ordered_quantity_is_zero_for_unused_stores(self) -> None:
        """Match-only runs order nothing, so every quantity stays zero."""
        rows = self._rows([_store(1, 21.0), _store(2, 15.0)])
        self.assertEqual([row["ordered_qty"] for row in rows], [0, 0])

    def test_split_quantities_accumulate_per_store(self) -> None:
        """A store selected twice must sum, not overwrite."""
        stores = [_store(1, 21.0)]
        rows = self._rows(stores, selections=[(stores[0], 6), (stores[0], 4)])
        self.assertEqual(rows[0]["ordered_qty"], 10)

    def test_source_is_recorded(self) -> None:
        """Distinguishes complete store_details data from CSV-imported winners."""
        rows = self._rows([_store(1, 21.0)], source="store_details")
        self.assertEqual(rows[0]["source"], "store_details")

    def test_rows_without_an_orderable_id_are_skipped(self) -> None:
        """A row with no store_product_id cannot key the products dimension."""
        rows = self._rows([_store(1, 21.0), {"storeId": 9, "storeName": "X"}])
        self.assertEqual(len(rows), 1)

    def test_synthetic_dom_rows_are_skipped(self) -> None:
        """dom-row-* ids are placeholders, not real Tawreed product ids."""
        dom = _store(2, 15.0, storeProductId="dom-row-abc")
        rows = self._rows([_store(1, 21.0), dom])
        self.assertEqual([row["store_product_id"] for row in rows], ["2900001"])

    def test_duplicate_store_products_are_collapsed(self) -> None:
        """The primary key forbids duplicates, so they must merge here first."""
        rows = self._rows([_store(1, 21.0), _store(1, 21.0)])
        self.assertEqual(len(rows), 1)

    def test_missing_prices_become_null_not_zero(self) -> None:
        """Zero prices would corrupt every average and minimum."""
        bare = {"storeId": 5, "storeName": "X", "storeProductId": 77}
        row = self._rows([bare])[0]
        self.assertIsNone(row["public_price"])
        self.assertIsNone(row["purchase_price"])

    def test_zero_stock_stores_are_kept(self) -> None:
        """An out-of-stock store is a fact worth tracking over time."""
        rows = self._rows([_store(1, 21.0, qty=0)])
        self.assertEqual(rows[0]["available_qty"], 0)


class DimensionRowTests(unittest.TestCase):
    """Dimension rows keep display values and first/last seen timestamps."""

    def test_store_dimension_uses_store_level_identity(self) -> None:
        """storeProductId must never become a store key."""
        row = store_dimension_row(_store(1, 21.0), _NOW)
        self.assertEqual(row["store_key"], "storeId:1")
        self.assertEqual(row["store_name"], "شركه 1")

    def test_product_dimension_carries_both_names(self) -> None:
        """Arabic and English names are both needed by the UI."""
        row = product_dimension_row(_store(1, 21.0), _NOW)
        self.assertEqual(row["store_product_id"], "2900001")
        self.assertEqual(row["product_id"], "2505")
        self.assertEqual(row["name_en"], "CAL MAG 30 F.C. TABLETS")
        self.assertEqual(row["name_ar"], "كال ماج 30 اقراص")

    def test_product_dimension_flags_synthetic_rows(self) -> None:
        """DOM fallback products must be distinguishable from real ones."""
        row = product_dimension_row(_store(1, 21.0, storeProductId="dom-row-x"), _NOW)
        self.assertEqual(row["is_synthetic"], 1)

    def test_dimension_timestamps_start_equal(self) -> None:
        """first_seen_at is never updated later, so it must be right now."""
        row = store_dimension_row(_store(1, 21.0), _NOW)
        self.assertEqual(row["first_seen_at"], row["last_seen_at"])


if __name__ == "__main__":
    unittest.main()
