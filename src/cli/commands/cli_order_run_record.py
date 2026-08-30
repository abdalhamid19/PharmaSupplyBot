"""Order-run database record wiring for the CLI order command.

Bridges the artifact-run context and CLI arguments into the fail-safe
persistence layer. Kept out of ``cli_order_execution`` so the runner keeps one
responsibility and this mapping stays independently testable.
"""

from __future__ import annotations

from typing import Any

from src.core.artifact_run import current_artifact_run
from src.core.ordering.order_run_persistence import (
    finish_run_record,
    open_run_record,
)


def active_run_key() -> str:
    """Return the run key for the active artifact run, or an empty string."""
    run = current_artifact_run()
    if run is None:
        return ""
    return f"{run.profile_key}/{run.run_id}"


def order_run_options(app_config, args, artifact_dir: str) -> dict[str, Any]:
    """Return the ``runs`` metadata for this order run.

    CLI overrides take precedence over configured defaults, matching what
    ``apply_order_overrides`` does to the live strategy, so the recorded values
    describe the run that actually executed.
    """
    warehouse = getattr(app_config, "warehouse_strategy", {}) or {}
    return {
        "mode": "match-only" if getattr(args, "match_only", False) else "order",
        "execution_mode": str(getattr(args, "execution_mode", "") or ""),
        "warehouse_mode": _warehouse_mode(warehouse, args),
        "min_discount_pct": _min_discount(warehouse, args),
        "matching_risk": str(getattr(args, "matching_risk_policy", "") or ""),
        "excel_source": str(getattr(args, "excel", "") or ""),
        "item_workers": _item_workers(app_config, args),
        "artifact_dir": artifact_dir,
    }


def open_order_run_record(app_config, profile_key: str, args, run) -> str | None:
    """Record the start of one order run and return its run key."""
    return open_run_record(
        profile_key,
        run.run_id,
        order_run_options(app_config, args, str(run.directory)),
        _persistence_options(app_config),
    )


def finish_order_run_record(app_config, run_key: str | None) -> None:
    """Mark one order run finished, tolerating a failed open."""
    finish_run_record(run_key or "", _persistence_options(app_config))


def _persistence_options(app_config) -> dict[str, Any]:
    """Return the database persistence options from application config."""
    database = getattr(app_config, "database", None)
    return database.persistence_options() if database else {}


def _warehouse_mode(warehouse: dict[str, Any], args) -> str:
    """Return the effective warehouse-selection mode for this run."""
    override = getattr(args, "warehouse_mode", None)
    return str(override or warehouse.get("mode", "") or "")


def _min_discount(warehouse: dict[str, Any], args) -> float | None:
    """Return the effective minimum-discount threshold for this run."""
    override = getattr(args, "min_discount_percent", None)
    value = override if override is not None else warehouse.get("min_discount_percent")
    return None if value is None else float(value)


def _item_workers(app_config, args) -> int:
    """Return the effective item-worker count for this run."""
    from .item_worker import resolve_item_workers

    return int(resolve_item_workers(app_config, args))


__all__ = [
    "active_run_key",
    "order_run_options",
    "open_order_run_record",
    "finish_order_run_record",
]
