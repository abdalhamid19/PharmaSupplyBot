"""Warning logger for non-fatal order-run persistence failures.

Separate from the persistence functions so the logger object is importable by
tests without pulling in the database modules.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("src.core.ordering.order_run_persistence")


def log_persistence_warning(message: str, **context: Any) -> None:
    """Log one non-fatal persistence failure with its traceback and context."""
    logger.warning(
        "%s (non-fatal): %s",
        message,
        ", ".join(f"{key}={value}" for key, value in context.items()),
        exc_info=True,
    )


__all__ = ["logger", "log_persistence_warning"]
