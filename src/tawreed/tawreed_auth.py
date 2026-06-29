"""Tawreed authentication flow management - unified module."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from playwright.sync_api import Page

from .tawreed_login_detection import (
    is_logged_in_marker_visible as marker_visible,
    login_detected,
)


# ============================================================================
# Token expiry helpers (from tawreed_auth_tokens.py)
# ============================================================================

def is_token_expired(state_path: Path) -> bool:
    """Check if the Tawreed access token in the state file expired or is missing."""
    token = access_token_from_state(state_path)
    return _is_jwt_expired(token)


def access_token_from_state(state_path: Path) -> str:
    """Read the Tawreed access token from the saved browser localStorage state."""
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    for origin in state.get("origins", []):
        token = _access_token_from_origin(origin)
        if token:
            return token
    return ""


def customer_id_from_state(state_path: Path) -> int:
    """Extract customer ID from JWT token in state file."""
    token = access_token_from_state(state_path)
    if not token:
        return 0
    
    payload = _jwt_payload(token)
    # Customer ID is in 'sub' field of JWT
    customer_id = payload.get("sub", "0")
    try:
        return int(customer_id)
    except (ValueError, TypeError):
        return 0


def _access_token_from_origin(origin: dict) -> str:
    """Return the access token from one Playwright storage-state origin."""
    if origin.get("origin") != "https://seller.tawreed.io":
        return ""
    for item in origin.get("localStorage", []):
        if item.get("name") == "access-token":
            return str(item.get("value", ""))
    return ""


def _is_jwt_expired(token: str) -> bool:
    """Return whether a JWT is expired, malformed, or near expiry."""
    payload = _jwt_payload(token)
    if not payload:
        return True
    exp = int(payload.get("exp", 0))
    return int(time.time()) >= (exp - 60)


def _jwt_payload(token: str) -> dict:
    """Decode a JWT payload without validating its signature."""
    if not token:
        return {}
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    try:
        payload_encoded = _base64url_with_padding(parts[1])
        payload_bytes = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_bytes)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _base64url_with_padding(value: str) -> str:
    """Return a base64url string padded to a decodable length."""
    padding = 4 - (len(value) % 4)
    if padding == 4:
        return value
    return value + ("=" * padding)


def headless_auth_failure_message() -> str:
    """Return the explicit auth failure used when hosted login never leaves the login page."""
    return (
        "Headless login failed: login form is still visible after waiting.\n"
        "Possible causes:\n"
        "- CAPTCHA/OTP required (headless mode cannot handle human verification)\n"
        "- Incorrect credentials in TAWREED_EMAIL/TAWREED_PASSWORD\n"
        "- Tawreed login page changed (selectors may need updating)\n"
        "Try interactive login with --auth-interactive instead."
    )


# ============================================================================
# Polling helpers (from tawreed_auth_waits.py)
# ============================================================================

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


# ============================================================================
# Auth flow class (from tawreed_auth_flow.py)
# ============================================================================

class TawreedAuthFlow:
    """Handles Tawreed authentication operations."""

    def __init__(self, bot):
        """Initialize auth flow with bot instance."""
        self.bot = bot

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        self._auth(wait_seconds=wait_seconds, headless=False)

    def auth_headless(self, wait_seconds: int = 120) -> None:
        """Run a headless login attempt and persist session state when credentials succeed."""
        self._auth(wait_seconds=wait_seconds, headless=True)

    def _auth(self, wait_seconds: int, headless: bool) -> None:
        """Authenticate in either interactive or headless mode and save session state."""
        from .tawreed_session import perform_tawreed_auth
        perform_tawreed_auth(self.bot, wait_seconds, headless)

    def _headless_auth_error(self) -> Exception:
        """Return the explicit auth failure used when hosted login never leaves the login page."""
        return RuntimeError(headless_auth_failure_message())

    def ensure_valid_auth(self) -> None:
        """Verify token is valid or refresh authentication automatically."""
        from .tawreed_auto_auth import auto_refresh_auth_if_needed

        auto_refresh_auth_if_needed(
            self.bot.config.base_url,
            self.bot.state_path,
            self.bot.config.runtime,
            self.bot.selectors,
            self.bot.profile_key,
            auth_lock=self.bot.auth_lock,
            worker_id=self.bot.worker_id,
        )


__all__ = [
    # Token helpers
    "is_token_expired",
    "access_token_from_state",
    "customer_id_from_state",
    # Wait helpers
    "wait_for_login_detection",
    "is_logged_in_marker_visible",
    # Wait internals (for session)
    "_initial_wait_state",
    "_advance_wait_state",
    "_wait_budget_ms",
    "_save_state_if_due",
    # Auth flow
    "TawreedAuthFlow",
    "headless_auth_failure_message",
]
