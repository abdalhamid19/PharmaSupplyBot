"""Polling helpers used while waiting for Tawreed login detection."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from .tawreed_login_detection import (
    is_logged_in_marker_visible as marker_visible,
    login_detected,
)

def wait_for_login_detection(
    page: Page, context, wait_seconds: int, email_sel: str, pwd_sel: str,
    marker: str, state_path: Path, save_session_state, save_inter: bool = True,
) -> bool:
    """Poll the page until the logged-in marker appears or timeout is reached."""
    ws = _initial_wait_state(wait_seconds)
    while ws["total_waited_ms"] < ws["wait_budget_ms"]:
        if login_detected(page, ws["poll_ms"], email_sel, pwd_sel, marker):
            return True
        _advance_wait_state(ws, context, state_path, save_session_state, save_inter)
    return False



def _initial_wait_state(wait_seconds: int) -> dict[str, int]:
    """Return the mutable polling state used while waiting for login detection."""
    return {
        "poll_ms": 2000,
        "save_every_ms": 5000,
        "total_waited_ms": 0,
        "since_last_save_ms": 0,
        "wait_budget_ms": _wait_budget_ms(wait_seconds),
    }


def _advance_wait_state(
    wait_state: dict[str, int],
    context,
    state_path: Path,
    save_session_state,
    save_intermediate: bool,
) -> None:
    """Advance the polling state and save session state when the interval is due."""
    poll_ms = wait_state["poll_ms"]
    wait_state["total_waited_ms"] += poll_ms
    wait_state["since_last_save_ms"] += poll_ms
    wait_state["since_last_save_ms"] = _save_state_if_due(
        context,
        state_path,
        wait_state["since_last_save_ms"],
        wait_state["save_every_ms"],
        save_session_state,
        save_intermediate,
    )


def is_logged_in_marker_visible(page: Page, logged_in_marker: str, timeout_ms: int) -> bool:
    """Return whether the configured logged-in marker appears within the timeout."""
    return marker_visible(page, logged_in_marker, timeout_ms)


def _wait_budget_ms(wait_seconds: int) -> int:
    """Return the total wait budget in milliseconds."""
    return max(1, int(wait_seconds)) * 1000


def _save_state_if_due(
    context,
    state_path: Path,
    since_last_save_ms: int,
    save_every_ms: int,
    save_session_state,
    save_intermediate: bool,
) -> int:
    """Persist intermediate session state when the save interval has elapsed."""
    if not save_intermediate:
        return 0 if since_last_save_ms >= save_every_ms else since_last_save_ms
    if since_last_save_ms < save_every_ms:
        return since_last_save_ms
    save_session_state(context, state_path, is_intermediate=True)
    return 0
