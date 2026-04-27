"""Environment helpers for Streamlit subprocess execution."""

from __future__ import annotations

import os


def merged_env(env_overrides: dict[str, str] | None) -> dict[str, str]:
    """Return the subprocess environment with any non-empty overrides applied."""
    env = dict(os.environ)
    for key, value in (env_overrides or {}).items():
        if value:
            env[key] = value
    return env
