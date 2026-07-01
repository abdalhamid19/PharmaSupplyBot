"""Bounded query-result cache helpers for Tawreed searches."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

MAX_QUERY_CACHE_SIZE = 16


class QueryResultCache:
    """Bounded, insertion-ordered (FIFO) query results cache."""

    def __init__(self, max_size: int = 256):
        self._max_size = max_size
        self._store: dict[str, list[dict[str, Any]]] = {}

    def get(self, query: str) -> list[dict[str, Any]] | None:
        """Retrieve cached results for a query."""
        return self._store.get(query)

    def put(self, query: str, value: list[dict[str, Any]]) -> None:
        """Store results for a query, evicting the oldest if full."""
        if query in self._store:
            self._store.pop(query)
        elif len(self._store) >= self._max_size:
            self._store.pop(next(iter(self._store)))
        self._store[query] = value


def get_bot_query_cache(bot) -> QueryResultCache:
    """Return the shared query cache for the bot, creating it if needed."""
    cache = getattr(bot, "_query_cache", None)
    if cache is None:
        size = 256
        if hasattr(bot, "config") and hasattr(bot.config, "matching"):
            size = getattr(bot.config.matching, "query_cache_size", 256)
        cache = QueryResultCache(max_size=size)
        try:
            bot._query_cache = cache
        except AttributeError:
            pass
    return cache


def cached_query_result(
    cache: dict[str, list[dict[str, Any]]] | QueryResultCache,
    query: str,
    fetch: Callable[[], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return cached query results while bounding per-item memory growth."""
    if isinstance(cache, QueryResultCache):
        val = cache.get(query)
        if val is not None:
            return val
        val = fetch()
        cache.put(query, val)
        return val

    if query in cache:
        return cache[query]
    if len(cache) >= MAX_QUERY_CACHE_SIZE:
        cache.pop(next(iter(cache)))
    cache[query] = fetch()
    return cache[query]
