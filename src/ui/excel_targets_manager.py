"""In-app management of Excel target catalogs.

The user can add and remove Excel target catalogs from the Streamlit
UI without editing ``state/config.yaml`` by hand. The manager reads
the YAML, mutates the ``excel_targets`` section, writes it back, and
mirrors the uploaded catalog bytes under
``artifacts/uploaded-excel-targets/<key>.xlsx``.

A second section, ``user_added_targets``, keeps the list of target
keys the operator added from the UI. Only those entries expose a
trash button in the checkbox group, so the operator cannot
accidentally remove a hard-coded warehouse from the config.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .streamlit_uploads import ARTIFACTS_DIR


USER_ADDED_KEY = "user_added_targets"
DEFAULT_TARGET_NAME = "المخازن الادويه المباشرة"


@dataclass(frozen=True)
class ExcelTargetAddResult:
    """The outcome of one add-target request."""

    target_key: str
    catalog_path: Path
    config_path: Path


def _normalise_name(name: str) -> str:
    """Return a YAML-safe and filename-safe slug for one target name.

    The slug is composed of ASCII letters/digits joined by single
    underscores. Arabic letters have no NFKD decomposition, so a name
    like ``المخازن الادويه المباشرة`` ends up as empty after the
    ASCII filter — in that case we fall back to a short hash of the
    original so two distinct Arabic names do not collide.
    """
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", name))
    cleaned = cleaned.strip("_").lower()
    if cleaned:
        return cleaned
    digest = abs(hash(name)) % (10**6)
    return f"target_{digest:06d}"


def _unique_key(base: str, existing: dict[str, Any]) -> str:
    """Return a key derived from ``base`` that does not yet exist in ``existing``."""
    if base not in existing:
        return base
    for index in range(2, 1000):
        candidate = f"{base}_{index}"
        if candidate not in existing:
            return candidate
    raise ValueError(f"Could not derive a unique target key from {base!r}")


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML config file, returning an empty dict if it does not exist."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)
    return dict(parsed or {})


def _write_yaml(path: Path, raw: dict[str, Any]) -> None:
    """Persist the YAML config back to disk using UTF-8 + LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    dumped = yaml.safe_dump(
        raw,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=10000,
    )
    path.write_text(dumped, encoding="utf-8")


def user_added_targets(config_path: Path) -> list[str]:
    """Return the list of target keys the operator added from the UI."""
    raw = _read_yaml(config_path)
    values = raw.get(USER_ADDED_KEY) or []
    if not isinstance(values, list):
        return []
    return [str(v) for v in values]


def add_excel_target(
    config_path: Path,
    display_name: str,
    uploaded_file,
    name_col: str = "صنف",
    price_col: str = "سعر",
    discount_col: str = "الخصم",
    code_col: str = "",
) -> ExcelTargetAddResult:
    """Add one Excel target catalog to the config and write the bytes to disk.

    The new key is derived from ``display_name`` and appended to the
    ``user_added_targets`` list so the UI can offer a trash button. The
    catalog bytes are written under
    ``artifacts/uploaded-excel-targets/<key>.xlsx``.
    """
    raw = _read_yaml(config_path)
    excel_targets = dict(raw.get("excel_targets") or {})
    slug = _normalise_name(display_name)
    target_key = _unique_key(slug, excel_targets)
    suffix = Path(getattr(uploaded_file, "name", f"{target_key}.xlsx")).suffix or ".xlsx"
    catalog_path = ARTIFACTS_DIR / "uploaded-excel-targets" / f"{target_key}{suffix}"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_bytes(uploaded_file.getvalue())

    excel_targets[target_key] = {
        "name_col": name_col,
        "price_col": price_col,
        "discount_col": discount_col,
        "code_col": code_col,
        "sheet": "",
        "header_row": 0,
        "enabled": True,
    }
    user_added = list(raw.get(USER_ADDED_KEY) or [])
    if target_key not in user_added:
        user_added.append(target_key)

    raw["excel_targets"] = excel_targets
    raw[USER_ADDED_KEY] = user_added
    _write_yaml(config_path, raw)
    return ExcelTargetAddResult(
        target_key=target_key,
        catalog_path=catalog_path,
        config_path=config_path,
    )


def remove_excel_target(config_path: Path, target_key: str) -> bool:
    """Remove one operator-added Excel target from the config.

    Returns ``True`` when something was actually removed. Refuses to
    remove keys that were not flagged as user-added (the operator
    would otherwise accidentally drop a hard-coded warehouse).
    """
    raw = _read_yaml(config_path)
    user_added = list(raw.get(USER_ADDED_KEY) or [])
    if target_key not in user_added:
        return False
    excel_targets = dict(raw.get("excel_targets") or {})
    excel_targets.pop(target_key, None)
    user_added = [key for key in user_added if key != target_key]
    raw["excel_targets"] = excel_targets
    raw[USER_ADDED_KEY] = user_added
    _write_yaml(config_path, raw)
    return True


__all__ = [
    "ExcelTargetAddResult",
    "DEFAULT_TARGET_NAME",
    "USER_ADDED_KEY",
    "user_added_targets",
    "add_excel_target",
    "remove_excel_target",
    "_normalise_name",
]
