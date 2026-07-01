"""Artifact capture helpers for Tawreed Playwright failures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

from .tawreed_artifacts_io import (
    _artifact_path,
    _active_artifact_subdir,
    _artifacts_dir,
    _ensure_csv_schema,
    _csv_artifact_fieldnames,
    _append_csv_rows,
    _csv_header_fieldnames,
    _rewrite_csv_artifact_with_fieldnames,
    _merge_row_fieldnames,
    _open_or_create_workbook,
    _xlsx_artifact_fieldnames,
    _ensure_xlsx_header_row,
    _append_xlsx_rows,
    _xlsx_header_fieldnames,
    _xlsx_rows,
    _rewrite_xlsx_worksheet_with_fieldnames,
)
from ..core.cart_removal_items import CartRemovalItem
from ..core.cart_removal_summary import CartRemovalSummary


def dump_artifacts(page: Page, profile_key: str, label: str, details: str = "") -> None:
    """Persist screenshot, HTML, and URL artifacts for debugging failures."""
    try:
        artifacts_dir = _artifacts_dir(profile_key)
        screenshot_path = _artifact_path(profile_key, label, None, ".png")
        html_path = _artifact_path(profile_key, label, None, ".html")
        text_path = _artifact_path(profile_key, label, None, ".txt")
        _write_screenshot_artifact(page, screenshot_path)
        _write_html_artifact(page, html_path)
        _write_text_artifact(page, text_path, details)
        print(f"[{profile_key}] Saved artifacts to: {artifacts_dir}")
    except Exception:
        pass


def write_text_artifact(profile_key: str, label: str, content: str) -> Path:
    """Write a plain-text diagnostic artifact for the active profile."""
    artifact_path = _artifact_path(profile_key, label, None, ".txt")
    artifact_path.write_text(content, encoding="utf-8")
    return artifact_path


def append_text_artifact(
    profile_key: str,
    label: str,
    content: str,
    label_suffix: str | None = None,
) -> Path:
    """Append plain-text diagnostic content to a profile artifact."""
    artifact_path = _artifact_path(profile_key, label, label_suffix, ".txt")
    with artifact_path.open("a", encoding="utf-8") as artifact_file:
        artifact_file.write(content)
    return artifact_path


def append_csv_artifact(
    profile_key: str,
    label: str,
    rows: list[dict[str, object]],
    label_suffix: str | None = None,
) -> Path | None:
    """Append structured diagnostic rows to a CSV artifact for the active profile."""
    if not rows:
        return None
    artifact_path = _artifact_path(profile_key, label, label_suffix, ".csv")
    fieldnames = _csv_artifact_fieldnames(artifact_path, rows)
    _ensure_csv_schema(artifact_path, fieldnames)
    _append_csv_rows(artifact_path, fieldnames, rows)
    return artifact_path


def append_xlsx_artifact(
    profile_key: str,
    label: str,
    rows: list[dict[str, object]],
    label_suffix: str | None = None,
) -> Path | None:
    """Append structured rows to an XLSX artifact for the active profile."""
    if not rows:
        return None
    try:
        artifact_path = _artifact_path(profile_key, label, label_suffix, ".xlsx")
        workbook, worksheet = _open_or_create_workbook(artifact_path)
        fieldnames = _xlsx_artifact_fieldnames(worksheet, rows)
        _ensure_xlsx_header_row(worksheet, fieldnames)
        _append_xlsx_rows(worksheet, fieldnames, rows)
        workbook.save(artifact_path)
        return artifact_path
    except PermissionError:
        _log_xlsx_permission_error(profile_key, label)
        return None


def _log_xlsx_permission_error(profile_key: str, label: str) -> None:
    """Print a friendly message when an XLSX artifact is open elsewhere."""
    print(f"[{profile_key}] Could not update {label}.xlsx; close it and retry.")


def _write_screenshot_artifact(page: Page, screenshot_path: Path) -> None:
    """Write a full-page screenshot when artifact capture is requested."""
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
    except Exception:
        pass


def _write_html_artifact(page: Page, html_path: Path) -> None:
    """Write prettified HTML content for offline inspection."""
    try:
        html_content = page.content()
        pretty_html = html_content.replace("><", ">\n<")
        html_path.write_text(pretty_html, encoding="utf-8")
    except Exception:
        pass


def _write_text_artifact(page: Page, text_path: Path, details: str) -> None:
    """Write lightweight text diagnostics for the current page state."""
    try:
        content = f"url={page.url}\n"
        if details:
            content += details
        text_path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def append_cart_removal_summary(
    profile_key: str,
    item: CartRemovalItem,
    summary: CartRemovalSummary,
    label_suffix: str | None = None,
) -> None:
    """Append one cart-removal summary row."""
    row = {
        "item_code": item.code,
        "item_name": item.name,
        "removed_count": summary.removed_count,
        "status": summary.status,
        "reason": summary.reason,
    }
    append_csv_artifact(
        profile_key, "cart_removal_summary", [row], label_suffix=label_suffix
    )


__all__ = [
    "dump_artifacts",
    "write_text_artifact",
    "append_text_artifact",
    "append_csv_artifact",
    "append_xlsx_artifact",
    "append_cart_removal_summary",
]
