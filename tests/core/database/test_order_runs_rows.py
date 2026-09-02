"""Tests for converting order-run objects into database rows."""

from __future__ import annotations

import unittest

from src.core.database.order_runs_meta import run_meta_row
from src.core.database.order_runs_rows import (
    item_dimension_row,
    order_run_item_key,
    run_item_row,
)
from src.core.manual_review.manual_review_hints import hint_key


class OrderRunItemKeyTests(unittest.TestCase):
    """The item key must match the manual-review store so joins stay possible."""

    def test_key_joins_normalized_code_and_name(self) -> None:
        """hint_key uppercases both parts and strips punctuation from the name."""
        self.assertEqual(order_run_item_key("12345", "cal mag"), "12345::CAL MAG")

    def test_key_matches_manual_review_hint_key(self) -> None:
        """A drift here would silently break every join to saved decisions."""
        code_key, name_key = hint_key("12345", "CAL MAG")
        self.assertEqual(order_run_item_key("12345", "CAL MAG"), f"{code_key}::{name_key}")

    def test_key_strips_excel_float_suffix(self) -> None:
        """Excel writes 001.0; both forms must resolve to one item."""
        self.assertEqual(
            order_run_item_key(" 001.0 ", " Panadol   Extra "),
            order_run_item_key("001", "panadol extra"),
        )

    def test_key_survives_missing_code(self) -> None:
        """Name-only rows still produce a usable key."""
        self.assertEqual(order_run_item_key("", "CAL MAG"), "::CAL MAG")

    def test_key_preserves_arabic_names(self) -> None:
        """Arabic item names are the common case in this project."""
        self.assertEqual(
            order_run_item_key("2505", "كال ماج 30 اقراص"),
            "2505::كال ماج 30 اقراص",
        )


class RunItemRowTests(unittest.TestCase):
    """Row conversion must accept both live objects and CSV strings."""

    def _summary(self, **overrides) -> dict[str, object]:
        row = {
            "item_code": "12345",
            "item_name": "CAL MAG",
            "item_qty": 10,
            "status": "added-to-cart",
            "reason": "Added to cart.",
            "ordered_total_qty": 10,
            "matched": True,
            "manual_review_required": False,
            "manual_review_category": "",
            "matched_query": "CAL MAG 30",
            "deterministic_score": 24.5,
            "winner_store_product_id": "2902379",
            "tie_break_reason": "exact match",
            "elapsed_seconds": 3.25,
            "match_elapsed_seconds": 1.5,
        }
        row.update(overrides)
        return row

    def test_maps_quantities_and_status(self) -> None:
        """Requested and ordered quantities come from different summary keys."""
        row = run_item_row("wardany/20260830_1809", self._summary())
        self.assertEqual(row["run_key"], "wardany/20260830_1809")
        self.assertEqual(row["item_key"], "12345::CAL MAG")
        self.assertEqual(row["requested_qty"], 10)
        self.assertEqual(row["ordered_qty"], 10)
        self.assertEqual(row["status"], "added-to-cart")

    def test_converts_python_booleans_to_integers(self) -> None:
        """SQLite has no boolean type."""
        row = run_item_row("r", self._summary(matched=True, manual_review_required=True))
        self.assertEqual(row["matched"], 1)
        self.assertEqual(row["manual_review_required"], 1)

    def test_converts_csv_boolean_strings(self) -> None:
        """db-import reads 'True'/'False' text from the summary CSV."""
        row = run_item_row("r", self._summary(matched="True", manual_review_required="False"))
        self.assertEqual(row["matched"], 1)
        self.assertEqual(row["manual_review_required"], 0)

    def test_empty_score_becomes_null_not_zero(self) -> None:
        """A no-results item has no score; 0.0 would corrupt averages."""
        row = run_item_row("r", self._summary(deterministic_score=""))
        self.assertIsNone(row["deterministic_score"])

    def test_empty_quantity_becomes_zero(self) -> None:
        """Quantities are counts, so absent means zero rather than unknown."""
        row = run_item_row("r", self._summary(ordered_total_qty=""))
        self.assertEqual(row["ordered_qty"], 0)

    def test_numeric_strings_are_parsed(self) -> None:
        """CSV import supplies every number as text."""
        row = run_item_row("r", self._summary(item_qty="10", deterministic_score="24.5"))
        self.assertEqual(row["requested_qty"], 10)
        self.assertAlmostEqual(float(row["deterministic_score"]), 24.5)

    def test_float_quantity_is_rounded(self) -> None:
        """openpyxl returns 10.0 for integer cells."""
        self.assertEqual(run_item_row("r", self._summary(item_qty=10.0))["requested_qty"], 10)

    def test_counts_default_to_zero(self) -> None:
        """Optional diagnostic counts are absent in legacy summary CSVs."""
        row = run_item_row("r", self._summary())
        self.assertEqual(row["candidates_considered"], 0)
        self.assertEqual(row["stores_offering"], 0)

    def test_explicit_counts_are_preserved(self) -> None:
        """Live runs supply candidate and store counts from the decision."""
        row = run_item_row(
            "r", self._summary(), candidates_considered=7, stores_offering=22
        )
        self.assertEqual(row["candidates_considered"], 7)
        self.assertEqual(row["stores_offering"], 22)

    def test_winner_store_key_is_optional(self) -> None:
        """Phase 2 has no store snapshot yet, so the winner store may be unknown."""
        self.assertIsNone(run_item_row("r", self._summary())["winner_store_key"])

    def test_matched_names_default_to_empty(self) -> None:
        """Legacy CSVs without matched-name columns still load with empty strings."""
        row = run_item_row("r", self._summary())
        self.assertEqual(row["matched_name_ar"], "")
        self.assertEqual(row["matched_name_en"], "")

    def test_matched_names_are_propagated(self) -> None:
        """The matched product's Arabic + English name is forwarded to run_items."""
        row = run_item_row(
            "r",
            self._summary(
                matched_product_name_ar="كال ماج 30 اقراص",
                matched_product_name_en="CAL MAG 30 TABS",
            ),
        )
        self.assertEqual(row["matched_name_ar"], "كال ماج 30 اقراص")
        self.assertEqual(row["matched_name_en"], "CAL MAG 30 TABS")


class ItemDimensionRowTests(unittest.TestCase):
    """The items dimension keeps the first display values it ever sees."""

    def test_carries_original_code_and_name(self) -> None:
        """The key is normalized but the display values are not."""
        row = item_dimension_row("12345", " CAL MAG ", "2026-08-30T18:09:00")
        self.assertEqual(row["item_key"], "12345::CAL MAG")
        self.assertEqual(row["item_code"], "12345")
        self.assertEqual(row["item_name"], "CAL MAG")

    def test_keeps_lowercase_display_name_verbatim(self) -> None:
        """Display values must not inherit the key's uppercasing."""
        row = item_dimension_row("12345", "cal mag", "2026-08-30T18:09:00")
        self.assertEqual(row["item_name"], "cal mag")
        self.assertEqual(row["item_key"], "12345::CAL MAG")

    def test_sets_both_timestamps_on_first_write(self) -> None:
        """first_seen_at is never updated later, so it must be set here."""
        row = item_dimension_row("1", "X", "2026-08-30T18:09:00")
        self.assertEqual(row["first_seen_at"], row["last_seen_at"])


class RunMetaRowTests(unittest.TestCase):
    """Run metadata makes cross-run comparisons interpretable."""

    def test_builds_run_key_from_profile_and_run_id(self) -> None:
        """run_id alone is not unique across profiles in the same minute."""
        row = run_meta_row("wardany", "20260830_1809", started_at="2026-08-30T18:09:00")
        self.assertEqual(row["run_key"], "wardany/20260830_1809")
        self.assertEqual(row["profile_key"], "wardany")
        self.assertEqual(row["run_id"], "20260830_1809")

    def test_records_strategy_options(self) -> None:
        """Comparing prices across runs is meaningless without these."""
        row = run_meta_row(
            "wardany",
            "1",
            started_at="2026-08-30T18:09:00",
            warehouse_mode="max_discount",
            min_discount_pct=15.0,
            mode="match-only",
            execution_mode="auto",
        )
        self.assertEqual(row["warehouse_mode"], "max_discount")
        self.assertAlmostEqual(float(row["min_discount_pct"]), 15.0)
        self.assertEqual(row["mode"], "match-only")
        self.assertEqual(row["execution_mode"], "auto")

    def test_finished_at_is_null_while_running(self) -> None:
        """An unfinished run must be distinguishable from a completed one."""
        self.assertIsNone(
            run_meta_row("p", "1", started_at="2026-08-30T18:09:00")["finished_at"]
        )


if __name__ == "__main__":
    unittest.main()
