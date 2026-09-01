"""Shared helpers for the Run DB drilldown tests.

Patches the page module's local read-function bindings (Streamlit binds
``from order_runs_read import fetch_runs`` at the top of the page, so
patching the source module alone does not intercept the call). The
drilldown dialogs import their filter helpers lazily, so we also seed
stub callables on the source module so the dialog import resolves.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.core.database import order_runs_read as _read_module
from .drilldown_app_test import build_app_test, build_dialog_app_test
from .drilldown_app_test import stop_app_test_patches

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
    }
    row.update(overrides)
    return row


__all__ = [
    "RUN_KEY", "item_row", "run_row",
    "build_app_test", "build_dialog_app_test", "stop_app_test_patches",
]