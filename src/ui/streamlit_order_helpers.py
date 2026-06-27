"""Form value helpers for Streamlit order tab."""

from __future__ import annotations


def _int_form_value(form_values: dict[str, object], key: str, default: int) -> int:
    """Return one integer form value with a safe fallback."""
    return int(str(form_values.get(key, default) or default))


def _float_form_value(
    form_values: dict[str, object], key: str, default: float
) -> float:
    """Return one float form value with a safe fallback."""
    return float(str(form_values.get(key, default) or default))


def _append_optional_ai_text(args: list[str], flag: str, value: object) -> None:
    """Append an optional text CLI flag."""
    text = str(value or "").strip()
    if text:
        args.extend([flag, text])
