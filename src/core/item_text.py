"""Shared item text normalization helpers."""

from __future__ import annotations


def normalized_key(code: object, name: object) -> tuple[str, str]:
    """Return a normalized comparable product key."""
    return normalize_code(code), normalize_name(name)


def normalize_code(value: object) -> str:
    """Return a stable code string for comparisons."""
    text = normalized_cell_text(value).lower()
    if text in {"nan", "none"}:
        return ""
    if text.endswith(".0"):
        return text[:-2]
    return text


def normalize_name(value: object) -> str:
    """Return a stable item-name string for comparisons."""
    return " ".join(normalized_cell_text(value).lower().split())


def normalized_cell_text(value: object) -> str:
    """Return spreadsheet cell text safely without pandas artifacts."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip()


def display_code_text(value: object) -> str:
    """Return code text suitable for saving and display."""
    text = normalized_cell_text(value)
    if text.endswith(".0"):
        return text[:-2]
    return text
