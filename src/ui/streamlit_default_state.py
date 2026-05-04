"""Default session-state resolution for the Streamlit GUI."""

from __future__ import annotations

import os
from base64 import b64decode
from binascii import Error as BinasciiError
from pathlib import Path

import streamlit as st


DEFAULT_STATE_DIR = Path("state_defaults")


def default_state_bytes(profile_key: str) -> bytes | None:
    """Return default session-state bytes from disk, secrets, or environment."""
    disk_path = DEFAULT_STATE_DIR / f"{profile_key}.json"
    if disk_path.exists():
        return disk_path.read_bytes()
    env_bytes = env_default_state_bytes(profile_key)
    if env_bytes is not None:
        return env_bytes
    return secret_default_state_bytes(profile_key)


def env_default_state_bytes(profile_key: str) -> bytes | None:
    """Return default session-state bytes from profile-specific environment variables."""
    raw_json = os.getenv(default_state_env_name(profile_key))
    if raw_json:
        return raw_json.encode("utf-8")
    encoded_json = os.getenv(default_state_b64_env_name(profile_key))
    if not encoded_json:
        return None
    try:
        return b64decode(encoded_json)
    except BinasciiError:
        return None


def secret_default_state_bytes(profile_key: str) -> bytes | None:
    """Return default session-state bytes from Streamlit secrets when configured."""
    raw_json = streamlit_secret_value(secret_default_state_key(profile_key))
    if raw_json:
        return str(raw_json).encode("utf-8")
    encoded_json = streamlit_secret_value(secret_default_state_b64_key(profile_key))
    if not encoded_json:
        return None
    try:
        return b64decode(str(encoded_json))
    except BinasciiError:
        return None


def streamlit_secret_value(key: str) -> object | None:
    """Return one Streamlit secret value when available."""
    try:
        return st.secrets.get(key)
    except Exception:  # noqa: BLE001
        return None


def default_state_env_name(profile_key: str) -> str:
    """Return the raw-JSON environment variable name for one profile."""
    return f"PHARMASUPPLYBOT_STATE_{profile_key.upper()}_JSON"


def default_state_b64_env_name(profile_key: str) -> str:
    """Return the base64 environment variable name for one profile."""
    return f"PHARMASUPPLYBOT_STATE_{profile_key.upper()}_B64"


def secret_default_state_key(profile_key: str) -> str:
    """Return the raw-JSON Streamlit secrets key for one profile."""
    return f"default_state_{profile_key}"


def secret_default_state_b64_key(profile_key: str) -> str:
    """Return the base64 Streamlit secrets key for one profile."""
    return f"default_state_{profile_key}_b64"
