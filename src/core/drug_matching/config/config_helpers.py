"""Small configuration helpers shared by local matching code."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Set the matching package log level without adding handlers."""
    logging.getLogger("src.core.drug_matching").setLevel(
        getattr(logging, level.upper(), logging.INFO)
    )


__all__ = ["setup_logging"]
