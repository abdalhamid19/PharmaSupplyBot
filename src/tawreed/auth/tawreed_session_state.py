"""Session state management for Tawreed authentication."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..tawreed_login_detection import login_detected


logger = logging.getLogger(__name__)


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


def wait_for_login_detection(
    page: Page,
    context,
    wait_seconds: int,
    email_sel: str,
    pwd_sel: str,
    marker: str,
    state_path: Path,
    save_session_state,
    save_inter: bool = True,
) -> bool:
    """Poll the page until the logged-in marker appears or timeout is reached."""
    ws = _initial_wait_state(wait_seconds)
    while ws["total_waited_ms"] < ws["wait_budget_ms"]:
        if login_detected(page, ws["poll_ms"], email_sel, pwd_sel, marker):
            return True
        _advance_wait_state(ws, context, state_path, save_session_state, save_inter)
    return False


def auth_temp_state_path(state_path: Path) -> Path:
    """Return the temporary path used while validating a newly captured auth session."""
    return state_path.with_name(f"{state_path.stem}.tmp{state_path.suffix}")


def save_session_state(context, state_path: Path, is_intermediate: bool) -> None:
    """Persist the current browser storage state to disk."""
    try:
        context.storage_state(path=str(state_path))
        if is_intermediate:
            logger.debug(
                "saved intermediate session state",
                extra={"state_path": str(state_path)},
            )
    except Exception:
        pass


def promote_session_state(temp_state_path: Path, final_state_path: Path) -> None:
    """Replace the final saved session state with a validated temporary capture."""
    final_state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_state_path.replace(final_state_path)


def discard_session_state(state_path: Path) -> None:
    """Delete one temporary or invalid saved session state without surfacing cleanup errors."""
    try:
        state_path.unlink(missing_ok=True)
    except Exception:
        pass


__all__ = [
    "auth_temp_state_path",
    "save_session_state",
    "promote_session_state",
    "discard_session_state",
    "wait_for_login_detection",
]
