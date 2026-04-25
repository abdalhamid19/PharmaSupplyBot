from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class ExcelConfig:
    code_col: str
    name_col: str
    qty_col: str
    min_qty: int = 1
    max_qty: int = 10**9


@dataclass(frozen=True)
class ProfileConfig:
    display_name: str
    pharmacy_switch: dict[str, Any]


@dataclass(frozen=True)
class RuntimeConfig:
    headless: bool = True
    slow_mo_ms: int = 0
    timeout_ms: int = 45000


@dataclass(frozen=True)
class AppConfig:
    base_url: str
    excel: ExcelConfig
    profiles: dict[str, ProfileConfig]
    selectors: dict[str, Any]
    warehouse_strategy: dict[str, Any]
    runtime: RuntimeConfig

    def profiles_to_run(self, profile: str | None, all_profiles: bool) -> list[tuple[str, ProfileConfig]]:
        if all_profiles:
            return list(self.profiles.items())
        if profile:
            if profile not in self.profiles:
                raise KeyError(f"Unknown profile '{profile}'. Available: {', '.join(self.profiles.keys())}")
            return [(profile, self.profiles[profile])]
        if len(self.profiles) == 1:
            k = next(iter(self.profiles.keys()))
            return [(k, self.profiles[k])]
        raise SystemExit("Please provide --profile <name> or use --all-profiles")


def _require(d: dict[str, Any], key: str) -> Any:
    if key not in d:
        raise KeyError(f"Missing required config key: {key}")
    return d[key]


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Create it by copying config.example.yaml to config.yaml"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    site = _require(raw, "site")
    excel = _require(raw, "excel")
    profiles_raw = _require(raw, "profiles")

    profiles: dict[str, ProfileConfig] = {}
    for k, v in profiles_raw.items():
        profiles[k] = ProfileConfig(
            display_name=str(v.get("display_name", k)),
            pharmacy_switch=dict(v.get("pharmacy_switch", {"enabled": False, "pharmacy_name": ""})),
        )

    runtime_raw = dict(raw.get("runtime", {}))
    runtime = RuntimeConfig(
        headless=bool(runtime_raw.get("headless", True)),
        slow_mo_ms=int(runtime_raw.get("slow_mo_ms", 0)),
        timeout_ms=int(runtime_raw.get("timeout_ms", 45000)),
    )

    return AppConfig(
        base_url=str(site.get("base_url", "https://seller.tawreed.io/#/login")),
        excel=ExcelConfig(
            code_col=str(excel.get("code_col", "كود")),
            name_col=str(excel.get("name_col", "إسم الصنف")),
            qty_col=str(excel.get("qty_col", "كمية النقص")),
            min_qty=int(excel.get("min_qty", 1)),
            max_qty=int(excel.get("max_qty", 10**9)),
        ),
        profiles=profiles,
        selectors=dict(raw.get("selectors", {})),
        warehouse_strategy=dict(raw.get("warehouse_strategy", {})),
        runtime=runtime,
    )

