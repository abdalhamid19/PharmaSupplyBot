"""AppTest builders for the Run DB drilldown tests.

Extracted from conftest.py so the conftest stays within the audit
function-length cap. See conftest.py for the rationale behind patching
the page module's local read-function bindings and seeding stub filter
helpers on the source read module.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.core.database import order_runs_read as _read_module


_DIALOG_FILTER_FOR_FUNCTION = {
    "show_matched_dialog": "fetch_run_items_matched",
    "show_flagged_dialog": "fetch_run_items_flagged",
    "show_not_orderable_dialog": "fetch_run_items_not_orderable",
    "show_ordered_dialog": "fetch_run_items_ordered",
}


def _seed_filter_helpers(matched, flagged, not_orderable, ordered) -> None:
    """Pre-seed stub filter helpers on the source read module."""
    _read_module.fetch_run_items_matched = lambda run_key: list(matched)
    _read_module.fetch_run_items_flagged = lambda run_key: list(flagged)
    _read_module.fetch_run_items_not_orderable = lambda rk: list(not_orderable)
    _read_module.fetch_run_items_ordered = lambda run_key: list(ordered)


def _build_patchers(run, items, store_row_count, item_stores, missed_discounts):
    """Return the list of patch objects for the page's read functions."""
    return [
        patch("src.ui.views.run_db.streamlit_run_db_page.fetch_runs",
              return_value=[run]),
        patch("src.ui.views.run_db.streamlit_run_db_page.fetch_run_items",
              return_value=items),
        patch("src.ui.views.run_db.streamlit_run_db_page.database_is_ready",
              return_value=True),
        patch("src.core.database.order_runs_read.run_store_row_count",
              return_value=store_row_count),
        patch("src.ui.views.run.db.streamlit_run_tables.fetch_item_stores"
              if False else
              "src.ui.views.run_db.streamlit_run_tables.fetch_item_stores",
              return_value=item_stores),
        patch("src.ui.views.run_db.streamlit_missed_discount."
              "fetch_missed_discounts", return_value=missed_discounts),
    ]


_DRIVER_SCRIPT_TEMPLATE = """
import sys
from unittest.mock import patch

RUN = {run}
ITEMS = {items}
STORE_ROW_COUNT = {store_row_count}
ITEM_STORES = {item_stores}
MISSED_DISCOUNTS = {missed_discounts}

with patch('src.ui.views.run_db.streamlit_run_db_page.fetch_runs', return_value=[RUN]), \\
     patch('src.ui.views.run_db.streamlit_run_db_page.fetch_run_items', return_value=ITEMS), \\
     patch('src.ui.views.run_db.streamlit_run_db_page.database_is_ready', return_value=True), \\
     patch('src.core.database.order_runs_read.run_store_row_count', return_value=STORE_ROW_COUNT), \\
     patch('src.ui.views.run_db.streamlit_run_tables.fetch_item_stores', return_value=ITEM_STORES), \\
     patch('src.ui.views.run_db.streamlit_missed_discount.fetch_missed_discounts', return_value=MISSED_DISCOUNTS):
    from src.ui.views.run_db.streamlit_run_db_page import render_run_db_tab
    render_run_db_tab()
"""


def build_app_test(
    *,
    run: dict[str, Any] | None = None,
    items: list[dict[str, Any]] | None = None,
    matched: list[dict[str, Any]] | None = None,
    flagged: list[dict[str, Any]] | None = None,
    not_orderable: list[dict[str, Any]] | None = None,
    ordered: list[dict[str, Any]] | None = None,
    store_row_count: int = 0,
    item_stores: list[dict[str, Any]] | None = None,
    missed_discounts: list[dict[str, Any]] | None = None,
) -> AppTest:
    """Build an ``AppTest`` for the run DB tab with mock read-functions wired."""
    from .conftest import item_row, run_row
    run = run if run is not None else run_row()
    items = items if items is not None else [item_row(i) for i in range(3)]
    matched = list(matched) if matched is not None else []
    flagged = list(flagged) if flagged is not None else []
    not_orderable = list(not_orderable) if not_orderable is not None else []
    ordered = list(ordered) if ordered is not None else []
    item_stores = list(item_stores) if item_stores is not None else []
    missed_discounts = (
        list(missed_discounts) if missed_discounts is not None else []
    )
    script = _DRIVER_SCRIPT_TEMPLATE.format(
        run=repr(run), items=repr(items),
        store_row_count=store_row_count,
        item_stores=repr(item_stores),
        missed_discounts=repr(missed_discounts),
    )
    app = AppTest.from_string(script, default_timeout=30)
    app._drilldown_patchers = _build_patchers(
        run, items, store_row_count, item_stores, missed_discounts
    )
    for patcher in app._drilldown_patchers:
        patcher.start()
    _seed_filter_helpers(matched, flagged, not_orderable, ordered)
    return app


def stop_app_test_patches(app: AppTest) -> None:
    """Stop every patcher registered by :func:`build_app_test`."""
    for patcher in getattr(app, "_drilldown_patchers", []):
        patcher.stop()
    app._drilldown_patchers = []


def build_dialog_app_test(*, dialog: str, run_key: str,
                          rows: list[dict[str, Any]]) -> AppTest:
    """Build an ``AppTest`` that invokes one dialog function in isolation."""
    dialog_filter = _DIALOG_FILTER_FOR_FUNCTION.get(dialog)
    if dialog_filter is None:
        raise ValueError(f"Unknown dialog function: {dialog!r}")
    script = (
        "import sys\n"
        "from unittest.mock import patch\n"
        "import src.core.database.order_runs_read as read_mod\n"
        "read_mod.fetch_run_items_matched = lambda rk: []\n"
        "read_mod.fetch_run_items_flagged = lambda rk: []\n"
        "read_mod.fetch_run_items_not_orderable = lambda rk: []\n"
        "read_mod.fetch_run_items_ordered = lambda rk: []\n"
        f"with patch('src.core.database.order_runs_read.{dialog_filter}',"
        f" return_value={rows!r}):\n"
        "    from src.ui.views.run_db.streamlit_run_drilldown_dialogs import "
        f"{dialog}\n"
        f"    {dialog}({run_key!r})\n"
    )
    return AppTest.from_string(script, default_timeout=30)
