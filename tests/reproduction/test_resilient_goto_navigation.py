"""Tests for resilient_goto navigation timeout handling.

Regression: state/config.yaml timeout_ms=15000 + a transient cold TCP/TLS
stall (observed 21 s first-connect to seller.tawreed.io) crashed the whole
`order --match-only` run with Playwright TimeoutError inside
validate_saved_session -> page.goto.

Contract locked here:
  1. goto uses a navigation-grade floor (>= 60 s) regardless of the small
     runtime timeout_ms.
  2. A single transient timeout is retried once (and succeeds).
  3. A persistent timeout still raises after the retry.
  4. Non-timeout navigation errors propagate immediately (no retry).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tawreed.auth.tawreed_session import (  # noqa: E402
    NAVIGATION_TIMEOUT_FLOOR_MS, resilient_goto,
)
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError  # noqa: E402


class _FakePage:
    """Records goto calls; optionally fails N times with TimeoutError."""

    def __init__(self, failures: int = 0, error: Exception | None = None):
        self.calls: list[dict] = []
        self._failures = failures
        self._error = error or PlaywrightTimeoutError(
            "Page.goto: Timeout 15000ms exceeded."
        )

    def goto(self, url, wait_until=None, timeout=None):
        self.calls.append({"url": url, "wait_until": wait_until, "timeout": timeout})
        if self._failures > 0:
            self._failures -= 1
            raise self._error


class ResilientGotoTests(unittest.TestCase):
    def test_uses_navigation_floor_despite_small_default(self) -> None:
        page = _FakePage()
        resilient_goto(page, "https://example.test/#/catalog", timeout_ms=15000)
        self.assertEqual(len(page.calls), 1)
        self.assertGreaterEqual(page.calls[0]["timeout"], NAVIGATION_TIMEOUT_FLOOR_MS)
        self.assertGreaterEqual(NAVIGATION_TIMEOUT_FLOOR_MS, 60_000)
        self.assertEqual(page.calls[0]["wait_until"], "domcontentloaded")

    def test_transient_timeout_is_retried_once(self) -> None:
        page = _FakePage(failures=1)
        resilient_goto(page, "https://example.test/#/login", timeout_ms=15000)
        self.assertEqual(len(page.calls), 2, "exactly one retry expected")
        self.assertEqual(page.calls[0]["url"], page.calls[1]["url"])

    def test_persistent_timeout_still_raises(self) -> None:
        page = _FakePage(failures=2)
        with self.assertRaises(PlaywrightTimeoutError):
            resilient_goto(page, "https://example.test/#/login", timeout_ms=15000)
        self.assertEqual(len(page.calls), 2, "no infinite retry loop")

    def test_non_timeout_error_propagates_without_retry(self) -> None:
        page = _FakePage(error=RuntimeError("net::ERR_NAME_NOT_RESOLVED"))
        with self.assertRaises(RuntimeError):
            resilient_goto(page, "https://example.test/#/login", timeout_ms=15000)
        self.assertEqual(len(page.calls), 1, "only DNS-level errors are not retried")

    def test_no_timeout_argument_still_gets_floor(self) -> None:
        page = _FakePage()
        resilient_goto(page, "https://example.test/")
        self.assertGreaterEqual(page.calls[0]["timeout"], NAVIGATION_TIMEOUT_FLOOR_MS)


if __name__ == "__main__":
    unittest.main()
