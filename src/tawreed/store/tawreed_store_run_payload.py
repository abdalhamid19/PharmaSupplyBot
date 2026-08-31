"""Order-run database payload assembled from the active bot state.

Bridges the Tawreed bot (which holds the per-item store snapshot) and the
fail-safe persistence layer, so the artifact writer needs one helper call
instead of reaching into bot attributes itself.
"""

from __future__ import annotations

from typing import Any

from src.core.artifact_run import current_artifact_run

from .tawreed_store_snapshot import (
    captured_store_rows,
    captured_store_selections,
    captured_store_source,
)


def active_order_run_key() -> str:
    """Return the order-run database key for the active artifact run, if any."""
    run = current_artifact_run()
    return f"{run.profile_key}/{run.run_id}" if run else ""


def store_snapshot_payload(bot) -> dict[str, Any]:
    """Return the offering-store snapshot keywords for one item write."""
    return {
        "stores": captured_store_rows(bot),
        "store_selections": captured_store_selections(bot),
        "store_source": captured_store_source(bot),
    }


def persistence_options(bot) -> dict[str, Any] | None:
    """Return the configured database options, or ``None`` when unavailable."""
    database = getattr(getattr(bot, "config", None), "database", None)
    return database.persistence_options() if database is not None else None


__all__ = [
    "active_order_run_key",
    "store_snapshot_payload",
    "persistence_options",
]
