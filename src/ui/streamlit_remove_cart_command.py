"""Command building for remove-cart operations."""

from __future__ import annotations

from pathlib import Path


def remove_cart_command(
    config_path: Path,
    form_values: dict[str, object],
    excel_path: Path | None,
) -> list[str]:
    """Return CLI command arguments for one remove-cart run."""
    command = _remove_cart_base_command(config_path, form_values, excel_path)
    if form_values["profile_mode"] == "Single profile":
        command.extend(["--profile", str(form_values["profile_key"])])
    else:
        command.append("--all-profiles")
    if form_values.get("debug_browser"):
        command.append("--debug-browser")
    command.extend(["--execution-mode", str(form_values.get("execution_mode", "auto"))])
    item_workers = _form_int(form_values, "item_workers", 1)
    if item_workers > 1:
        command.extend(["--item-workers", str(item_workers)])
    return command


def _remove_cart_base_command(
    config_path: Path, form_values: dict[str, object], excel_path: Path | None
) -> list[str]:
    if _uses_saved_manual_review(form_values):
        return [
            "remove-cart", "--config", str(config_path),
            "--manual-review-scope", "saved-decisions",
            "--manual-decision", "not_matching",
        ]
    return ["remove-cart", "--config", str(config_path), "--excel", str(excel_path)]


def _uses_saved_manual_review(form_values: dict[str, object]) -> bool:
    return form_values.get("input_mode") == "Saved not matching manual review"


def _form_int(values: dict[str, object], key: str, default: int) -> int:
    """Return one integer form value with an empty-safe fallback."""
    value = values.get(key)
    if value is None or value == "":
        return default
    return int(value)
