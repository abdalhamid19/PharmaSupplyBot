"""SQLite connection management."""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class DatabasePool:
    """Manages SQLite connections for the manual-review store."""

    def __init__(self, credentials):
        """Initialize with credentials that provide a filesystem path."""
        self.credentials = credentials
        self.path: Path = Path(credentials.path)
        self._connected = False
        self._lock = threading.RLock()

    def connect(self) -> None:
        """Ensure the database directory exists and the file is reachable."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Touch/open once so connection errors surface early.
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
        self._connected = True
        logger.info("Connected to SQLite: %s", self.path)

    def close(self) -> None:
        """Mark the pool closed (connections are opened per use)."""
        self._connected = False
        logger.info("SQLite database closed: %s", self.path)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Open a short-lived SQLite connection (context manager)."""
        with self._lock:
            conn = sqlite3.connect(
                str(self.path),
                check_same_thread=False,
                timeout=30.0,
            )
            try:
                conn.execute("PRAGMA foreign_keys=ON")
                yield conn
            finally:
                conn.close()


__all__ = ["DatabasePool"]
