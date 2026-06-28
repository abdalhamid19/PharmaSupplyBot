"""Browser operations for Tawreed session management."""

from pathlib import Path
from typing import Any

from playwright.sync_api import Page

from .tawreed_playwright_browser import launch_chromium


def open_auth_page(pw, base_url: str, runtime, headless: bool = False) -> tuple[Any, Any, Page]:
    """Create a browser page for one-time authentication."""
    browser = launch_chromium(pw, headless=headless, slow_mo_ms=runtime.slow_mo_ms)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    page.goto(base_url, wait_until="domcontentloaded")
    return browser, context, page


def open_order_page(
    playwright,
    runtime,
    state_path: Path,
    debug_browser: bool = False,
) -> tuple[Any, Any, Page]:
    """Create an automated browser page using the saved session state."""
    browser = launch_chromium(
        playwright,
        headless=False if debug_browser else runtime.headless,
        slow_mo_ms=runtime.slow_mo_ms,
    )
    context = browser.new_context(storage_state=str(state_path))
    page = context.new_page()
    page.set_default_timeout(runtime.timeout_ms)
    return browser, context, page


def close_context(context) -> None:
    """Close the Playwright browser context without surfacing cleanup errors."""
    try:
        context.close()
    except Exception:
        pass


def close_browser(browser) -> None:
    """Close the Playwright browser without surfacing cleanup errors."""
    try:
        browser.close()
    except Exception:
        pass
