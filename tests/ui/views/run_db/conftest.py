"""Shared helpers for the Run DB tests.

Patches the page module's local read-function bindings (Streamlit binds
``from order_runs_read import fetch_runs`` at the top of the page, so
patching the source module alone does not intercept the call).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.core.database import order_runs_read as _read_module
from src.core.database import order_runs_read_filters as _filter_module

RUN_KEY = "tester/20260101_1200"
PROFILE_KEY = "tester"
RUN_ID = "20260101_1200"


def item_row(index: int, **overrides: Any) -> dict[str, Any]:
    """Return one row shaped like the live ``RUN_FACTS`` query yields."""
    row = {
        "item_key": f"k{index}", "item_code": f"c{index}",
        "item_name": f"N{index}", "requested_qty": 1, "ordered_qty": 0,
        "status": "matched-only", "reason": "", "matched": 1,
        "manual_review_required": 0, "stores_offering": 0,
        "winner_store_key": None, "elapsed_seconds": 0.0,
    }
    row.update(overrides)
    return row


def run_row(**overrides: Any) -> dict[str, Any]:
    """Return one run dict shaped like ``LIST_RUNS`` with overrides last."""
    row = {
        "run_key": RUN_KEY, "run_id": RUN_ID, "profile_key": PROFILE_KEY,
        "command": "order", "mode": "order",
        "started_at": "2026-01-01T12:00:00Z",
        "finished_at": "2026-01-01T12:01:00Z",
        "total_items": 3, "items": 3, "matched": 0, "flagged": 0,
        "added_to_cart": 0, "total_ordered": 0, "store_count": 0,
        "not_orderable": 0,
    }
    row.update(overrides)
    return row


def _seed_filter_helpers(matched, flagged, not_orderable, ordered) -> None:
    """Pre-seed stub filter helpers on both read modules."""
    _read_module.fetch_run_items_matched = lambda run_key: list(matched)
    _read_module.fetch_run_items_flagged = lambda run_key: list(flagged)
    _read_module.fetch_run_items_not_orderable = lambda rk: list(not_orderable)
    _read_module.fetch_run_items_ordered = lambda run_key: list(ordered)
    _filter_module.fetch_run_items_matched = lambda run_key, db=None: list(matched)
    _filter_module.fetch_run_items_flagged = lambda run_key, db=None: list(flagged)
    _filter_module.fetch_run_items_not_orderable = lambda rk, db=None: list(not_orderable)
    _filter_module.fetch_run_items_ordered = lambda run_key, db=None: list(ordered)


_DRIVER_SCRIPT_TEMPLATE = """
import sys
from unittest.mock import patch

RUN = {run}
ITEMS = {items}
STORE_ROW_COUNT = {store_row_count}
ITEM_STORES = {item_stores}
MISSED_DISCOUNTS = {missed_discounts}
MATCHED = {matched}
FLAGGED = {flagged}
NOT_ORDERABLE = {not_orderable}
ORDERED = {ordered}

with patch('src.ui.views.run_db.streamlit_run_db_page.fetch_runs', return_value=[RUN]), \\
     patch('src.ui.views.run_db.streamlit_run_db_page.fetch_run_items', return_value=ITEMS), \\
     patch('src.ui.views.run_db.streamlit_run_db_page.database_is_ready', return_value=True), \\
     patch('src.core.database.order_runs_read.run_store_row_count', return_value=STORE_ROW_COUNT), \\
     patch('src.ui.views.run_db.streamlit_run_tables.fetch_item_stores', return_value=ITEM_STORES), \\
     patch('src.ui.views.run_db.streamlit_missed_discount.fetch_missed_discounts', return_value=MISSED_DISCOUNTS), \\
     patch('src.core.database.order_runs_read_filters.fetch_run_items_matched', return_value=MATCHED), \\
     patch('src.core.database.order_runs_read_filters.fetch_run_items_flagged', return_value=FLAGGED), \\
     patch('src.core.database.order_runs_read_filters.fetch_run_items_not_orderable', return_value=NOT_ORDERABLE), \\
     patch('src.core.database.order_runs_read_filters.fetch_run_items_ordered', return_value=ORDERED):
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
        matched=repr(matched),
        flagged=repr(flagged),
        not_orderable=repr(not_orderable),
        ordered=repr(ordered),
    )
    app = AppTest.from_string(script, default_timeout=30)
    app._drilldown_patchers = [
        patch("src.ui.views.run_db.streamlit_run_db_page.fetch_runs",
              return_value=[run]),
        patch("src.ui.views.run_db.streamlit_run_db_page.fetch_run_items",
              return_value=items),
        patch("src.ui.views.run_db.streamlit_run_db_page.database_is_ready",
              return_value=True),
        patch("src.core.database.order_runs_read.run_store_row_count",
              return_value=store_row_count),
        patch("src.ui.views.run_db.streamlit_run_tables.fetch_item_stores",
              return_value=item_stores),
        patch("src.ui.views.run_db.streamlit_missed_discount."
              "fetch_missed_discounts", return_value=missed_discounts),
    ]
    for patcher in app._drilldown_patchers:
        patcher.start()
    return app


def stop_app_test_patches(app: AppTest) -> None:
    """Stop every patcher registered by :func:`build_app_test`."""
    for patcher in getattr(app, "_drilldown_patchers", []):
        patcher.stop()
    app._drilldown_patchers = []


__all__ = [
    "RUN_KEY", "PROFILE_KEY", "RUN_ID", "item_row", "run_row",
    "build_app_test", "stop_app_test_patches",
]
