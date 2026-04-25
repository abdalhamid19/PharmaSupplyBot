"""Configuration loading for the Tawreed bot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config_factory import (
    DEFAULT_BASE_URL,
    build_excel_config,
    build_matching_config,
    build_profiles,
    build_runtime_config,
)
from .config_models import AppConfig


def load_config(path: Path) -> AppConfig:
    """Load application settings from a YAML configuration file."""
    raw_values = _load_raw_config(path)
    site_values = _require(raw_values, "site")
    excel_values = _require(raw_values, "excel")
    profiles_values = _require(raw_values, "profiles")
    return AppConfig(
        base_url=str(site_values.get("base_url", DEFAULT_BASE_URL)),
        excel=build_excel_config(excel_values),
        profiles=build_profiles(profiles_values),
        selectors=dict(raw_values.get("selectors", {})),
        warehouse_strategy=dict(raw_values.get("warehouse_strategy", {})),
        matching=build_matching_config(raw_values),
        runtime=build_runtime_config(raw_values),
    )


def _load_raw_config(path: Path) -> dict[str, Any]:
    """Read the YAML configuration file from disk."""
    if not path.exists():
        raise FileNotFoundError(
            "Config file not found: "
            f"{path}. Create it by copying config.example.yaml to config.yaml"
        )
    raw_values = yaml.safe_load(path.read_text(encoding="utf-8"))
    _require(raw_values, "site")
    _require(raw_values, "excel")
    _require(raw_values, "profiles")
    return raw_values


def _require(values: dict[str, Any], key: str) -> Any:
    """Return a required config key or raise a descriptive error."""
    if key not in values:
        raise KeyError(f"Missing required config key: {key}")
    return values[key]
