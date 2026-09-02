"""Write plan assembly for one order-run item.

Separates "what rows will be written" from "how they are written", so the
writer mixin keeps only transaction handling and both halves stay small.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .order_runs_keys import item_dimension_row, order_run_item_key
from .order_runs_rows import run_item_row
from .order_runs_snapshot_writer import snapshot_fact_fields


@dataclass(frozen=True)
class ItemWritePlan:
    """Every row and key needed to persist one order-run item."""

    run_key: str
    item_key: str
    now: str
    item_row: dict[str, Any]
    fact_row: dict[str, Any]
    stores: tuple
    selections: tuple
    source: str


def item_write_plan(
    run_key: str,
    summary: dict[str, Any],
    now: str,
    snapshot: dict[str, Any],
    fact_fields: dict[str, Any],
) -> ItemWritePlan:
    """Return the write plan for one order-run item."""
    stores, selections, source = _snapshot_parts(snapshot)
    code, name = summary.get("item_code"), summary.get("item_name")
    return ItemWritePlan(
        run_key=run_key,
        item_key=order_run_item_key(code, name),
        now=now,
        item_row=item_dimension_row(code, name, now),
        fact_row=_fact_row(run_key, summary, stores, selections, fact_fields),
        stores=stores,
        selections=selections,
        source=source,
    )


def _snapshot_parts(snapshot: dict[str, Any]) -> tuple[tuple, tuple, str]:
    """Return the store rows, selections, and source from a snapshot payload."""
    return (
        tuple(snapshot.get("stores") or ()),
        tuple(snapshot.get("store_selections") or ()),
        str(snapshot.get("store_source") or ""),
    )


def _fact_row(
    run_key: str,
    summary: dict[str, Any],
    stores: tuple,
    selections: tuple,
    fact_fields: dict[str, Any],
) -> dict[str, Any]:
    """Return the ``run_items`` row with snapshot-derived fields merged in."""
    fields = dict(fact_fields)
    fields.update(snapshot_fact_fields(stores, selections))
    return run_item_row(run_key, summary, **fields)


def tawreed_fact_fields(profile_key: str) -> dict[str, str]:
    """Return the source fields that identify a Tawreed-profile match row."""
    return {"source_kind": "tawreed", "source_label": str(profile_key or "")}


def excel_target_fact_fields(target_key: str, source_file: str = "") -> dict[str, str]:
    """Return the source fields that identify an Excel-target match row.

    ``source_file`` carries the catalog file name (when the operator picked
    multiple files in the GUI). The ``source_label`` is stable for the same
    (target_key, file) tuple, so re-runs replace the row instead of
    duplicating it.
    """
    label = str(target_key or "")
    if source_file:
        label = f"{label}@{source_file}"
    return {"source_kind": "excel-target", "source_label": label}


__all__ = ["ItemWritePlan", "item_write_plan"]
