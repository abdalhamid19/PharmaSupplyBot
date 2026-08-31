"""Timestamp helpers for the order-runs database.

All stored timestamps are ISO-8601 UTC strings so runs recorded across daylight
saving changes still sort correctly, and so SQLite's ``date()`` and ``<``
comparisons work without a timezone-aware type.
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> str:
    """Return the current UTC time as a sortable ISO-8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()


def as_iso_utc(moment: datetime) -> str:
    """Return one datetime as a sortable ISO-8601 UTC string."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment.replace(microsecond=0).isoformat()


__all__ = ["utc_now", "as_iso_utc"]
