"""AppTest coverage for the in-page KPI filter bar on the Run Results tab.

These tests boot :func:`render_run_db_tab` under ``streamlit.testing.v1.AppTest``
without launching a real Streamlit server or opening the order-runs SQLite
database. Every read function the tab calls is replaced by deterministic
in-memory data so the assertions stay stable.

The helpers in :mod:`conftest` build a fully-wired AppTest; click tests
press a KPI button, run again, and assert the items table swaps rows.
"""

from __future__ import annotations

import unittest

from .conftest import (
    build_app_test,
    item_row,
    run_row,
    stop_app_test_patches,
)


def _button_labels(app) -> list[str]:
    """Return the labels of every KPI bar button currently rendered."""
    return [button.label for button in app.button]


def _kpi_button(app, label_prefix: str):
    """Return the first KPI button whose label starts with ``prefix``."""
    for index, button in enumerate(app.button):
        if button.label.startswith(label_prefix):
            return index, button
    raise AssertionError(
        f"No KPI button found starting with {label_prefix!r}; "
        f"rendered labels were {_button_labels(app)!r}"
    )


def _items_dataframe_rows(app) -> int:
    """Return the row count of the last dataframe (the items table)."""
    if not app.dataframe:
        return 0
    return app.dataframe[-1].value.shape[0]


class KpiFilterBarRenderingTests(unittest.TestCase):
    """KPI cards always render, even when their count is zero."""

    def setUp(self) -> None:
        self._app = build_app_test(
            run=run_row(matched=0, flagged=0, total_ordered=0,
                        not_orderable=0, store_count=0),
            items=[],
        )
        self._app.run()

    def tearDown(self) -> None:
        stop_app_test_patches(self._app)

    def test_kpi_filter_bar_renders_every_card_even_when_zero(self) -> None:
        """Every KPI card is visible; zero cards are disabled, not hidden."""
        self.assertEqual(self._app.exception, [])
        labels = _button_labels(self._app)
        self.assertIn("Matched · 0", labels)
        self.assertIn("Flagged · 0", labels)
        self.assertIn("Not-orderable · 0", labels)
        self.assertIn("Ordered qty · 0", labels)
        self.assertIn("Show all · 0", labels)

    def test_zero_count_buttons_are_disabled(self) -> None:
        """Buttons with a zero count must be disabled in AppTest state."""
        self.assertEqual(self._app.exception, [])
        for label in ("Matched · 0", "Flagged · 0", "Not-orderable · 0",
                      "Ordered qty · 0", "Show all · 0"):
            _, button = _kpi_button(self._app, label)
            self.assertTrue(
                button.disabled,
                f"{label!r} should be disabled at zero count",
            )


class KpiFilterBarClickTests(unittest.TestCase):
    """Clicking a KPI card toggles the items table to the filtered rows."""

    def tearDown(self) -> None:
        stop_app_test_patches(getattr(self, "_app", None))

    def _fresh_app(self, run_kwargs, **kwargs):
        full_items = [item_row(i, item_name=f"ITEM-{i}") for i in range(5)]
        self._app = build_app_test(
            run=run_row(**run_kwargs),
            items=full_items,
            **kwargs,
        )
        self._app.run()
        self.assertEqual(self._app.exception, [])
        return full_items

    def test_click_matched_card_filters_items_table(self) -> None:
        """Matched click should leave only matched rows in the items table."""
        matched_rows = [item_row(0, status="matched-only", matched=1)]
        self._fresh_app({"matched": 1, "items": 5}, matched=matched_rows)
        baseline = _items_dataframe_rows(self._app)
        self.assertEqual(baseline, 5)

        _, button = _kpi_button(self._app, "Matched")
        button.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])

        self.assertEqual(_items_dataframe_rows(self._app), 1)

    def test_click_show_all_clears_filter(self) -> None:
        """Show all should restore the unfiltered items table."""
        flagged_rows = [item_row(0, status="manual-review", matched=0,
                                 manual_review_required=1)]
        self._fresh_app({"flagged": 1, "items": 5}, flagged=flagged_rows)
        _, button = _kpi_button(self._app, "Flagged")
        button.click()
        self._app.run()
        self.assertEqual(_items_dataframe_rows(self._app), 1)

        _, show_all = _kpi_button(self._app, "Show all")
        show_all.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])
        self.assertEqual(_items_dataframe_rows(self._app), 5)

    def test_clicking_same_active_card_clears_filter(self) -> None:
        """Pressing the already-active card again toggles back to all items."""
        matched_rows = [item_row(0, status="matched-only", matched=1)]
        self._fresh_app({"matched": 1, "items": 5}, matched=matched_rows)
        _, matched_button = _kpi_button(self._app, "Matched")
        matched_button.click()
        self._app.run()
        self.assertEqual(_items_dataframe_rows(self._app), 1)

        matched_button = _kpi_button(self._app, "Matched")[1]
        matched_button.click()
        self._app.run()
        self.assertEqual(_items_dataframe_rows(self._app), 5)


if __name__ == "__main__":
    unittest.main()
