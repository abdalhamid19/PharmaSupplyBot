"""Tests for bounded Tawreed query caching."""

from __future__ import annotations

import unittest

from src.tawreed.tawreed_query_cache import (
    MAX_QUERY_CACHE_SIZE,
    QueryResultCache,
    cached_query_result,
)


class TawreedQueryCacheTests(unittest.TestCase):
    """Validate query-result cache reuse and size bounds."""

    def test_reuses_cached_query_without_refetching(self) -> None:
        calls = 0

        def fetch():
            nonlocal calls
            calls += 1
            return [{"productNameEn": "Panadol"}]

        cache = {}
        first = cached_query_result(cache, "Panadol", fetch)
        second = cached_query_result(cache, "Panadol", fetch)

        self.assertEqual(calls, 1)
        self.assertIs(first, second)

    def test_evicts_oldest_query_when_limit_is_reached(self) -> None:
        cache = {
            f"q{index}": [{"productNameEn": str(index)}]
            for index in range(MAX_QUERY_CACHE_SIZE)
        }

        cached_query_result(cache, "new", lambda: [{"productNameEn": "new"}])

        self.assertEqual(len(cache), MAX_QUERY_CACHE_SIZE)
        self.assertNotIn("q0", cache)
        self.assertIn("new", cache)

    def test_cache_hits_and_misses(self) -> None:
        """Check basic cache storage and retrieval."""
        cache = QueryResultCache(max_size=3)
        called_count = 0

        def fetch_data():
            nonlocal called_count
            called_count += 1
            return [{"id": called_count}]

        # First call: miss
        res1 = cached_query_result(cache, "query1", fetch_data)
        self.assertEqual(res1, [{"id": 1}])
        self.assertEqual(called_count, 1)

        # Second call: hit
        res2 = cached_query_result(cache, "query1", fetch_data)
        self.assertEqual(res2, [{"id": 1}])
        self.assertEqual(called_count, 1)

    def test_cache_eviction_bounded(self) -> None:
        """Check that cache respects max size limit and evicts oldest items."""
        cache = QueryResultCache(max_size=2)

        # Insert 2 queries
        cached_query_result(cache, "q1", lambda: [{"id": 1}])
        cached_query_result(cache, "q2", lambda: [{"id": 2}])

        # Insert 3rd query: q1 should be evicted (oldest)
        cached_query_result(cache, "q3", lambda: [{"id": 3}])

        # q1 should be a miss now
        called = False

        def fetch():
            nonlocal called
            called = True
            return [{"id": 99}]

        res = cached_query_result(cache, "q1", fetch)
        self.assertTrue(called)
        self.assertEqual(res, [{"id": 99}])
