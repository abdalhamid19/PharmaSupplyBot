"""Tawreed API exceptions."""

from __future__ import annotations


class TawreedApiUnavailable(RuntimeError):
    """Raised when Tawreed API endpoints are not available or fail."""


__all__ = ["TawreedApiUnavailable"]
