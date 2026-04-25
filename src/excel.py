from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ExcelConfig


@dataclass(frozen=True)
class Item:
    code: str
    name: str
    qty: int


def _to_int(x: Any) -> int:
    if x is None:
        return 0
    try:
        if pd.isna(x):
            return 0
    except Exception:
        pass
    try:
        return int(round(float(x)))
    except Exception:
        s = str(x).strip()
        if not s:
            return 0
        return int(float(s))


def load_items_from_excel(path: Path, cfg: ExcelConfig, limit: int = 0) -> list[Item]:
    if not path.exists():
        raise FileNotFoundError(f"Excel not found: {path}")

    df = pd.read_excel(path)
    for col in (cfg.code_col, cfg.name_col, cfg.qty_col):
        if col not in df.columns:
            raise KeyError(f"Missing required column '{col}' in Excel. Found: {list(df.columns)}")

    items: list[Item] = []
    for _, row in df.iterrows():
        code = str(row.get(cfg.code_col, "")).strip()
        name = str(row.get(cfg.name_col, "")).strip()
        qty = _to_int(row.get(cfg.qty_col))

        if not code and not name:
            continue
        if qty < cfg.min_qty:
            continue
        if qty > cfg.max_qty:
            qty = cfg.max_qty

        items.append(Item(code=code, name=name, qty=qty))
        if limit and len(items) >= limit:
            break

    return items

