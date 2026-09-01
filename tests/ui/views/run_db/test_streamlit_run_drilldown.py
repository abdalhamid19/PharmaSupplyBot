"""AppTest coverage for KPI drill-down buttons on the Run Results tab.

These tests boot :func:`render_run_db_tab` under ``streamlit.testing.v1.AppTest``
without launching a real Streamlit server or opening the order-runs SQLite
database. Every read function the tab (and its drilldown dialogs) calls is
replaced by deterministic in-memory data so the assertions stay stable.

The ``build_app_test`` helper in :mod:`conftest` wires the mocks and exposes
one ``AppTest`` instance per test. Each click-based test runs the page once,
then clicks the relevant button and runs again — ``AppTest`` lets the
dialog's fragment content reach ``at.dataframe`` even though ``st.dialog``
itself is not a first-class element on the testing API.
"""

from __future__ import annotations

import unittest

from .conftest import (
    RUN_KEY,
    build_app_test,
    build_dialog_app_test,
    item_row,
    run_row,
    stop_app_test_patches,
)


def _button_labels(app) -> list[str]:
    """Return the labels of every drilldown button currently rendered."""
    return [button.label for button in app.button]


def _drilldown_button(app, label_prefix: str):
    """Return the first drilldown button whose label starts with ``prefix``."""
    for index, button in enumerate(app.button):
        if button.label.startswith(label_prefix):
            return index, button
    raise AssertionError(
        f"No drilldown button found starting with {label_prefix!r}; "
        f"rendered labels were {_button_labels(app)!r}"
    )


def _dialog_dataframe_shape(app) -> tuple[int, ...]:
    """Return the shape of the last dataframe rendered (the dialog table)."""
    if not app.dataframe:
        raise AssertionError(
            "No dataframes rendered; expected the dialog to add at least one"
        )
    return tuple(app.dataframe[-1].value.shape)


class DrilldownButtonRenderingTests(unittest.TestCase):
    """KPI drilldown buttons must disappear when their count is zero."""

    def setUp(self) -> None:
        self._app = build_app_test(
            run=run_row(matched=0, flagged=0, total_ordered=0, store_count=0),
            items=[],
        )
        self._app.run()

    def tearDown(self) -> None:
        stop_app_test_patches(self._app)

    def test_drilldown_buttons_hidden_when_count_is_zero(self) -> None:
        """Every KPI button is skipped when its count field is 0."""
        self.assertEqual(self._app.exception, [])
        labels = _button_labels(self._app)
        self.assertEqual(
            labels,
            [],
            f"Expected zero KPI buttons, got {labels!r}",
        )


class DrilldownDialogClickTests(unittest.TestCase):
    """Clicking each drilldown button should open its filtered dialog."""

    def tearDown(self) -> None:
        stop_app_test_patches(getattr(self, "_app", None))

    def test_drilldown_matched_button_opens_dialog(self) -> None:
        matched_rows = [
            item_row(i, status="matched-only", matched=1)
            for i in range(17)
        ]
        self._app = build_app_test(
            run=run_row(matched=17),
            matched=matched_rows,
        )
        self._app.run()
        self.assertEqual(self._app.exception, [])

        index, button = _drilldown_button(self._app, "Matched")
        self.assertEqual(index, 1, "Matched button should appear after Items")

        baseline = len(self._app.dataframe)
        button.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])

        self.assertGreater(
            len(self._app.dataframe),
            baseline,
            "Matched click should add the dialog dataframe",
        )
        self.assertEqual(
            _dialog_dataframe_shape(self._app)[0],
            17,
            "Matched dialog should show 17 rows",
        )

    def test_drilldown_flagged_button_opens_dialog(self) -> None:
        flagged_rows = [
            item_row(
                i,
                status="manual-review",
                matched=0,
                manual_review_required=1,
            )
            for i in range(5)
        ]
        self._app = build_app_test(
            run=run_row(matched=0, flagged=5),
            flagged=flagged_rows,
        )
        self._app.run()
        self.assertEqual(self._app.exception, [])

        index, button = _drilldown_button(self._app, "Flagged")
        self.assertEqual(index, 1, "Flagged button should be the second button")

        baseline = len(self._app.dataframe)
        button.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])

        self.assertGreater(
            len(self._app.dataframe),
            baseline,
            "Flagged click should add the dialog dataframe",
        )
        self.assertEqual(
            _dialog_dataframe_shape(self._app)[0],
            5,
            "Flagged dialog should show 5 rows",
        )

    def test_drilldown_ordered_button_opens_dialog(self) -> None:
        ordered_rows = [
            item_row(
                i,
                status="added-to-cart",
                matched=1,
                ordered_qty=2,
            )
            for i in range(8)
        ]
        self._app = build_app_test(
            run=run_row(matched=0, flagged=0, total_ordered=8),
            items=[],
            ordered=ordered_rows,
        )
        self._app.run()
        self.assertEqual(self._app.exception, [])

        index, button = _drilldown_button(self._app, "Ordered qty")
        self.assertEqual(
            index,
            0,
            "Ordered qty should be the only visible button when other counts are 0",
        )

        baseline = len(self._app.dataframe)
        button.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])

        self.assertGreater(
            len(self._app.dataframe),
            baseline,
            "Ordered click should add the dialog dataframe",
        )
        self.assertEqual(
            _dialog_dataframe_shape(self._app)[0],
            8,
            "Ordered dialog should show 8 rows",
        )

    def test_drilldown_items_button_opens_full_table(self) -> None:
        """Items drilldown should show the unfiltered item table."""
        full_items = [item_row(i, item_name=f"ITEM-{i}") for i in range(4)]
        self._app = build_app_test(
            run=run_row(matched=0, flagged=0, total_ordered=0, items=4),
            items=full_items,
        )
        self._app.run()
        self.assertEqual(self._app.exception, [])

        index, button = _drilldown_button(self._app, "Items")
        self.assertEqual(index, 0, "Items button should be the first button")

        baseline = len(self._app.dataframe)
        button.click()
        self._app.run()
        self.assertEqual(self._app.exception, [])

        self.assertGreater(
            len(self._app.dataframe),
            baseline,
            "Items click should add the dialog dataframe",
        )
        self.assertEqual(
            _dialog_dataframe_shape(self._app)[0],
            4,
            "Items dialog should show all 4 rows",
        )


class DrilldownNotOrderableDialogTests(unittest.TestCase):
    """``show_not_orderable_dialog`` is not reachable from a KPI button.

    The current :mod:`streamlit_run_drilldown` file only exposes buttons
    for Items, Matched, Flagged, Offering stores, and Ordered qty — Not-
    orderable has a dialog but no button. To still cover the dialog's
    contract the test boots a small AppTest that calls the dialog directly
    and asserts the rendered dataframe matches the canned filter rows.
    """

    def test_drilldown_not_orderable_dialog_renders_filtered_rows(self) -> None:
        rows = [
            item_row(
                i,
                item_name=f"BLOCKED-{i}",
                status="not-orderable",
                matched=0,
            )
            for i in range(4)
        ]
        app = build_dialog_app_test(
            dialog="show_not_orderable_dialog",
            run_key=RUN_KEY,
            rows=rows,
        )
        app.run()
        self.assertEqual(app.exception, [])
        self.assertEqual(
            _dialog_dataframe_shape(app)[0],
            4,
            "Not-orderable dialog should show 4 rows",
        )


if __name__ == "__main__":
    unittest.main()