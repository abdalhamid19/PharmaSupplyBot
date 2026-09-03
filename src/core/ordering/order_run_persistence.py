"""Fail-safe bridge between the order run and the order-runs database.

Every function here swallows exceptions on purpose. An ``order run`` talks to a
live site and can add real items to a purchase cart; losing an analytics row is
recoverable (the CSV artifacts remain, and ``db-import`` can backfill), whereas
aborting a half-completed run is not. Failures are logged at WARNING with a
traceback so nothing is lost silently.
"""

from __future__ import annotations

from typing import Any

from .order_run_persistence_log import log_persistence_warning, logger

__all__ = [
    "logger",
    "persistence_enabled",
    "open_run_record",
    "record_run_item",
    "finish_run_record",
]


def persistence_enabled(options: dict[str, Any] | None) -> bool:
    """Return whether order-run persistence should write anything.

    A blank configured ``path`` is an explicit off switch rather than a fallback
    to the default location.
    """
    if options is None:
        return True
    if not options.get("enabled", True):
        return False
    return "path" not in options or bool(options.get("path"))


def open_run_record(
    profile_key: str,
    run_id: str,
    run_options: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> str | None:
    """Record the start of one run and return its run key, or ``None`` on failure."""
    if not persistence_enabled(options):
        return None
    try:
        from ..database.order_runs_meta import run_meta_row
        from ..database.order_runs_time import utc_now

        meta = run_meta_row(profile_key, run_id, started_at=utc_now(), **run_options)
        return _store(options).open_run(meta)
    except Exception:
        log_persistence_warning(
            "could not open order-run record", profile=profile_key, run_id=run_id
        )
        return None


def record_run_item(
    run_key: str,
    summary: dict[str, Any],
    options: dict[str, Any] | None = None,
    **fact_fields: Any,
) -> None:
    """Persist one item's facts, or log and continue when the write fails."""
    if not run_key or not persistence_enabled(options):
        return
    try:
        _store(options).upsert_run_item(run_key, summary, **fact_fields)
    except Exception:
        log_persistence_warning(
            "could not persist order-run item",
            run_key=run_key,
            item_code=str(summary.get("item_code", "")),
        )


def finish_run_record(run_key: str, options: dict[str, Any] | None = None) -> None:
    """Mark a run finished, or log and continue when the update fails."""
    if not run_key or not persistence_enabled(options):
        return
    try:
        _store(options).finish_run(run_key)
    except Exception:
        log_persistence_warning("could not finish order-run record", run_key=run_key)


def _store(options: dict[str, Any] | None):
    """Return the order-runs store for the configured database path."""
    from ..database.order_runs_store import OrderRunsStore

    return OrderRunsStore((options or {}).get("path"))
