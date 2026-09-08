"""Shared path defaults for CLI argument handling."""

from __future__ import annotations

from pathlib import Path


DEFAULT_CONFIG_PATH = Path("state/config.yaml")


def config_path_from_arguments(arguments: object) -> Path:
    """Return the config path from CLI arguments without changing its layout."""
    return Path(getattr(arguments, "config", DEFAULT_CONFIG_PATH))


__all__ = ["DEFAULT_CONFIG_PATH", "config_path_from_arguments"]
