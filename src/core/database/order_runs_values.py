"""Value coercion for order-run database rows.

The same row builders serve two callers with different value types: the live
order flow passes Python objects (``bool``, ``float``, ``None``) while
``db-import`` passes CSV text (``"True"``, ``"24.5"``, ``""``). These helpers
normalise both into the types SQLite columns expect.
"""

from __future__ import annotations

from typing import Any

_TRUE_TEXT = {"true", "1", "yes", "y", "t"}
_EMPTY_TEXT = {"", "none", "nan", "null"}


def as_int(value: Any, default: int = 0) -> int:
    """Return a rounded integer, using ``default`` for empty or invalid values.

    Quantities are counts, so an absent value means zero rather than unknown.
    """
    if isinstance(value, bool):
        return int(value)
    text = _text(value)
    if text.lower() in _EMPTY_TEXT:
        return default
    try:
        return int(round(float(text)))
    except (TypeError, ValueError):
        return default


def as_optional_float(value: Any) -> float | None:
    """Return a float, or ``None`` when the value is absent.

    Scores and prices must stay ``NULL`` when missing: coercing them to ``0.0``
    would silently drag every average and minimum toward zero.
    """
    text = _text(value)
    if text.lower() in _EMPTY_TEXT:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def as_flag(value: Any) -> int:
    """Return 1 or 0 for SQLite, accepting Python bools and CSV text."""
    if isinstance(value, bool):
        return int(value)
    return 1 if _text(value).lower() in _TRUE_TEXT else 0


def as_text(value: Any) -> str:
    """Return trimmed text, mapping placeholder values to an empty string."""
    text = _text(value)
    return "" if text.lower() in _EMPTY_TEXT else text


def as_optional_text(value: Any) -> str | None:
    """Return trimmed text, or ``None`` so foreign keys stay unset when absent."""
    return as_text(value) or None


def _text(value: Any) -> str:
    """Return a stripped string for any scalar, treating ``None`` as empty."""
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "as_int",
    "as_optional_float",
    "as_flag",
    "as_text",
    "as_optional_text",
]
