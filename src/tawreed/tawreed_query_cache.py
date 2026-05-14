"""Bounded query-result cache helpers for Tawreed searches."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

MAX_QUERY_CACHE_SIZE = 16


def cached_query_result(
    cache: dict[str, list[dict[str, Any]]],
    query: str,
    fetch: Callable[[], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return cached query results while bounding per-item memory growth."""
    if query in cache:
        return cache[query]
    if len(cache) >= MAX_QUERY_CACHE_SIZE:
        cache.pop(next(iter(cache)))
    cache[query] = fetch()
    return cache[query]
