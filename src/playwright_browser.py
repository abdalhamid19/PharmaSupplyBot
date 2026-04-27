"""Playwright browser launch helpers with lazy Chromium installation."""

from __future__ import annotations

import subprocess
import sys


def launch_chromium(playwright, headless: bool, slow_mo_ms: int):
    """Launch Chromium, installing the browser binary once if it is missing."""
    try:
        return _launch(playwright, headless, slow_mo_ms)
    except Exception as error:
        if not _missing_executable_error(error):
            raise
        _install_chromium()
        return _launch(playwright, headless, slow_mo_ms)


def _launch(playwright, headless: bool, slow_mo_ms: int):
    """Launch Chromium once with the requested runtime settings."""
    return playwright.chromium.launch(headless=headless, slow_mo=slow_mo_ms)


def _missing_executable_error(error: Exception) -> bool:
    """Return whether the Playwright error indicates a missing browser executable."""
    return "Executable doesn't exist" in str(error)


def _install_chromium() -> None:
    """Install the Playwright Chromium browser binary for the current interpreter."""
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
        text=True,
        capture_output=True,
    )
