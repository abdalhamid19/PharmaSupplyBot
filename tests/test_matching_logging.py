"""Tests for queue-backed matching logging."""
from __future__ import annotations

import logging
import unittest
from logging.handlers import QueueHandler

from src.core.matching_trace import async_matching_logging


class MatchingLoggingTests(unittest.TestCase):
    """Validate safe setup and shutdown for async matching logs."""

    def test_async_matching_logging_uses_queue_handler_and_stops_listener(self) -> None:
        with async_matching_logging("CRITICAL") as logger:
            self.assertEqual(logger.level, logging.CRITICAL)
            self.assertIsInstance(logger.handlers[0], QueueHandler)
            logger.debug("trace message")
        self.assertFalse(logger.propagate)


if __name__ == "__main__":
    unittest.main()
