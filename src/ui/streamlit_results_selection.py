"""Command/profile/run selection functions for results tab."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .streamlit_shared import ARTIFACTS_DIR


def command_options() -> list[str]:
    """Return artifact commands that have run folders."""
    names = ["order", "match-products", "export-products", "remove-cart"]
    return [name for name in names if (ARTIFACTS_DIR / name).is_dir()]


def command_profile_options(command: str) -> list[str]:
    """Return profile folders for one artifact command."""
    root = ARTIFACTS_DIR / command
    profiles = sorted(path.name for path in root.iterdir() if path.is_dir())
    return profiles or ["wardany"]


def command_run_options(command: str, profile_key: str) -> list[str]:
    """Return run folders for one command/profile pair."""
    root = ARTIFACTS_DIR / command / profile_key
    runs = sorted((path.name for path in root.iterdir() if path.is_dir()), reverse=True)
    return runs or [""]
