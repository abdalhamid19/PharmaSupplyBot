"""Main Excel utilities for Tawreed order items."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..config.config_models import ExcelConfig
from .excel_readers import load_items_from_excel, load_match_only_items_from_excel


@dataclass(frozen=True)
class Item:
    """One requested product row loaded from the shortage Excel sheet."""

    code: str
    name: str
    qty: int


__all__ = ["Item", "load_items_from_excel", "load_match_only_items_from_excel"]
