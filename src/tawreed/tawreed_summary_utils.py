"""Utility functions for Tawreed order summaries."""

from ..core.utils.excel import Item
from .tawreed_dialogs import visible_overlay_diagnostics


def _item_error_label(item: Item) -> str:
    """Return the artifact label for one failed item."""
    return f"item_error_{item.code or 'no_code'}"


def _item_error_details(page, item: Item, error: Exception) -> str:
    """Build diagnostic artifact details for one failed item."""
    return _artifact_details(
        _item_error_label(item),
        error,
        overlay_diagnostics=visible_overlay_diagnostics(page),
        item_code=item.code,
        item_name=item.name,
        item_qty=item.qty,
    )


def _artifact_details(label: str, error: Exception, **extra: object) -> str:
    """Build plain-text diagnostic details for saved failure artifacts."""
    lines = [f"label={label}", f"error_type={type(error).__name__}", f"error={error}"]
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _console_safe(text: str) -> str:
    """Return text that can be printed on cp1252 Windows consoles without crashing."""
    return text.encode("cp1252", errors="replace").decode("cp1252")
