"""Playwright browser launch helpers with lazy Chromium installation."""

from __future__ import annotations

import subprocess
import sys


def launch_chromium(playwright, headless: bool, slow_mo_ms: int):
    """Launch Chromium, installing the browser binary once if it is missing."""
    try:
        return _launch(playwright, headless, slow_mo_ms)
    except Exception as error:
        _raise_if_missing_linux_runtime(error)
        if not _missing_executable_error(error):
            raise
        _install_chromium()
        try:
            return _launch(playwright, headless, slow_mo_ms)
        except Exception as retry_error:
            _raise_if_missing_linux_runtime(retry_error)
            raise


def _launch(playwright, headless: bool, slow_mo_ms: int):
    """Launch Chromium once with the requested runtime settings."""
    return playwright.chromium.launch(headless=headless, slow_mo=slow_mo_ms)


def _missing_executable_error(error: Exception) -> bool:
    """Return whether the Playwright error indicates a missing browser executable."""
    return "Executable doesn't exist" in str(error)


def _raise_if_missing_linux_runtime(error: Exception) -> None:
    """Raise a clearer error when Chromium is present but Linux shared libraries are missing."""
    error_text = str(error)
    if "error while loading shared libraries:" not in error_text:
        return
    missing_library = _missing_library_name(error_text)
    raise RuntimeError(
        "Chromium is installed but Linux runtime libraries are missing"
        f"{f' ({missing_library})' if missing_library else ''}. "
        "On Streamlit Community Cloud, add the required apt packages in packages.txt and redeploy."
    ) from error


def _missing_library_name(error_text: str) -> str:
    """Extract the missing shared-library name from one Playwright launch error."""
    marker = "error while loading shared libraries:"
    if marker not in error_text:
        return ""
    suffix = error_text.split(marker, 1)[1].strip()
    return suffix.split(":", 1)[0].strip()


def _install_chromium() -> None:
    """Install the Playwright Chromium browser binary for the current interpreter."""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        text=True,
        capture_output=True,
    )
