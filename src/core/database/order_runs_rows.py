"""Row builders that turn order summaries into ``run_items`` fact rows.

Kept free of SQL so the mapping is unit-testable without a database, and so the
live order flow and ``db-import`` provably produce identical rows from the same
summary shape.
"""

from __future__ import annotations

from typing import Any

from .order_runs_keys import item_dimension_row, order_run_item_key, run_key_for
from .order_runs_values import (
    as_flag,
    as_int,
    as_optional_float,
    as_optional_text,
    as_text,
)


def run_item_row(
    run_key: str,
    summary: dict[str, Any],
    candidates_considered: int = 0,
    stores_offering: int = 0,
    winner_store_key: str | None = None,
    winner_store_product_id: str | None = None,
    source_kind: str = "",
    source_label: str = "",
) -> dict[str, Any]:
    """Return one ``run_items`` fact row from an order summary row.

    ``winner_store_product_id`` overrides the summary value when the caller has
    an offering-store snapshot: that snapshot reflects the store actually
    ordered from, which is more authoritative than the matched candidate.

    ``source_kind`` / ``source_label`` identify which search surface produced
    this row: ``tawreed:<profile>`` for Tawreed profiles,
    ``excel-target:<key>[@<file>]`` for Excel target catalogs.
    """
    row = _identity_fields(
        run_key, summary, candidates_considered, stores_offering,
        source_kind, source_label,
    )
    row["winner_store_key"] = as_optional_text(winner_store_key)
    row.update(_quantity_and_status_fields(summary))
    row.update(_match_outcome_fields(summary, winner_store_product_id))
    return row


def _identity_fields(
    run_key: str,
    summary: dict[str, Any],
    candidates_considered: int,
    stores_offering: int,
    source_kind: str,
    source_label: str,
) -> dict[str, Any]:
    """Return the keys and diagnostic counts for one run item."""
    return {
        "run_key": run_key,
        "item_key": order_run_item_key(
            summary.get("item_code"), summary.get("item_name")
        ),
        "source_kind": as_text(source_kind),
        "source_label": as_text(source_label),
        "candidates_considered": as_int(candidates_considered),
        "stores_offering": as_int(stores_offering),
    }


def _quantity_and_status_fields(summary: dict[str, Any]) -> dict[str, Any]:
    """Return quantity, status, and timing fields for one run item."""
    return {
        "requested_qty": as_int(summary.get("item_qty")),
        "ordered_qty": as_int(summary.get("ordered_total_qty")),
        "status": as_text(summary.get("status")),
        "reason": as_text(summary.get("reason")),
        "elapsed_seconds": as_optional_float(summary.get("elapsed_seconds")) or 0.0,
        "match_elapsed_seconds": (
            as_optional_float(summary.get("match_elapsed_seconds")) or 0.0
        ),
    }


def _match_outcome_fields(
    summary: dict[str, Any], winner_store_product_id: str | None = None
) -> dict[str, Any]:
    """Return match, review, and winner fields for one run item."""
    winner_id = winner_store_product_id or summary.get("winner_store_product_id")
    return {
        "matched": as_flag(summary.get("matched")),
        "manual_review_required": as_flag(summary.get("manual_review_required")),
        "manual_review_category": as_text(summary.get("manual_review_category")),
        "matched_query": as_text(summary.get("matched_query")),
        "deterministic_score": as_optional_float(summary.get("deterministic_score")),
        "winner_store_product_id": as_optional_text(winner_id),
        "tie_break_reason": as_text(summary.get("tie_break_reason")),
    }


__all__ = [
    "order_run_item_key",
    "run_key_for",
    "item_dimension_row",
    "run_item_row",
]
