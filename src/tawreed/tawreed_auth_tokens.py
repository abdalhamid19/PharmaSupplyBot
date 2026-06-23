"""Token expiry helpers for saved Tawreed storage-state files."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path


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
