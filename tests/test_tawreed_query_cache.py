"""Tests for bounded Tawreed query caching."""

from __future__ import annotations

import unittest

from src.tawreed.tawreed_query_cache import MAX_QUERY_CACHE_SIZE, cached_query_result


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


if __name__ == "__main__":
    unittest.main()
