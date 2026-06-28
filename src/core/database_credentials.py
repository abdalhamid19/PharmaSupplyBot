"""Database credential loading and validation."""

from __future__ import annotations

import os
from dotenv import load_dotenv
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseCredentials:
    """Handles database credential loading and validation."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        sslmode: Optional[str] = None,
    ):
        """Initialize credentials from arguments or environment."""
        load_dotenv()
        self.host = host or os.getenv("DB_HOST")
        self.port = port or int(os.getenv("DB_PORT", "26257"))
        self.database = database or os.getenv("DB_NAME")
        self.user = user or os.getenv("DB_USER")
        self.password = password if password is not None else os.getenv("DB_PASSWORD")
        self.sslmode = sslmode or os.getenv("DB_SSLMODE", "require")
        self._validate_credentials()

    def _validate_credentials(self):
        """Validate required credentials are present."""
        if not self.host:
            raise RuntimeError("DB_HOST environment variable is required")
        if not self.database:
            raise RuntimeError("DB_NAME environment variable is required")
        if not self.user:
            raise RuntimeError("DB_USER environment variable is required")
        if not self.password:
            raise RuntimeError("DB_PASSWORD environment variable is required")


__all__ = ["DatabaseCredentials"]
