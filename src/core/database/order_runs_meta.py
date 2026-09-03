"""Run-metadata row builder for the ``runs`` table.

Kept separate from item-level row building because the fields come from a
different source: CLI arguments and application config rather than per-item
match results.
"""

from __future__ import annotations

from typing import Any

from .order_runs_keys import run_key_for
from .order_runs_schema import SCHEMA_VERSION
from .order_runs_values import as_int, as_optional_float, as_text


def run_meta_row(
    profile_key: str,
    run_id: str,
    started_at: str,
    command: str = "order",
    **options: Any,
) -> dict[str, Any]:
    """Return one ``runs`` row describing how this run was configured.

    Strategy options are stored because comparing prices or discounts between
    two runs is meaningless without knowing whether ``warehouse_mode`` or
    ``min_discount_pct`` changed between them.
    """
    row = _identity_fields(profile_key, run_id, started_at, command)
    row.update(_option_fields(options))
    return row


def _identity_fields(
    profile_key: str, run_id: str, started_at: str, command: str
) -> dict[str, Any]:
    """Return identity, timing, and schema fields for one run record."""
    return {
        "run_key": run_key_for(profile_key, run_id),
        "run_id": as_text(run_id),
        "profile_key": as_text(profile_key),
        "command": as_text(command) or "order",
        "started_at": started_at,
        "finished_at": None,
        "total_items": 0,
        "schema_version": SCHEMA_VERSION,
    }


def _option_fields(options: dict[str, Any]) -> dict[str, Any]:
    """Return the per-run strategy and source fields."""
    return {
        "mode": as_text(options.get("mode")),
        "execution_mode": as_text(options.get("execution_mode")),
        "warehouse_mode": as_text(options.get("warehouse_mode")),
        "min_discount_pct": as_optional_float(options.get("min_discount_pct")),
        "matching_risk": as_text(options.get("matching_risk")),
        "excel_source": as_text(options.get("excel_source")),
        "item_workers": as_int(options.get("item_workers"), default=1) or 1,
        "artifact_dir": as_text(options.get("artifact_dir")),
    }


__all__ = ["run_meta_row"]
