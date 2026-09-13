"""Store and warehouse selection helpers for Tawreed ordering flows."""

from __future__ import annotations
import logging

import re
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from ..store.tawreed_store_selection import (
    calculate_warehouse_priority_score,
    choose_next_store_for_remaining_quantity,
)

logger = logging.getLogger(__name__)


def choose_store_index(
    stores: list[dict[str, Any]],
    mode: str,
    skip_exception_cls: type[Exception],
    preferred_warehouses: list[str] | None = None,
    min_discount_percent: float = 0.0,
) -> int:
    """Choose the store index according to the configured warehouse strategy."""
    choice = choose_next_store_for_remaining_quantity(
        stores,
        mode=mode,
        skip_exception_cls=skip_exception_cls,
        preferred_warehouses=preferred_warehouses,
        min_discount_percent=min_discount_percent,
    )
    if choice is None:
        raise skip_exception_cls("All available stores for this product are out of stock.")
    return choice.index


def preferred_warehouse_row_index(
    rows,
    preferred_warehouses: list[str] | None = None,
    available_quantity_selector: str | None = None,
    min_discount_percent: float = 0.0,
) -> int | None:
    """Return the earliest in-stock row with the best configured priority."""
    candidates = _eligible_row_indexes(
        rows, available_quantity_selector, min_discount_percent
    )
    ranked = _best_priority_row_indexes(rows, candidates, preferred_warehouses or [])
    return ranked[0] if ranked else None


def _eligible_row_indexes(
    rows, quantity_selector: str | None, min_discount_percent: float = 0.0
) -> list[int]:
    indexes = list(range(rows.count()))
    if not quantity_selector:
        candidates = indexes
    else:
        candidates = [
            index
            for index in indexes
            if warehouse_row_quantity(rows.nth(index), quantity_selector) > 0
        ]
    if min_discount_percent <= 0:
        return candidates
    return [
        index
        for index in candidates
        if _warehouse_row_discount(rows.nth(index)) >= min_discount_percent - 0.001
    ]


def _best_priority_row_indexes(
    rows, indexes: list[int], preferred_warehouses: list[str]
) -> list[int]:
    if not indexes:
        return []
    priorities = [
        _warehouse_row_priority(rows.nth(index), preferred_warehouses)
        for index in indexes
    ]
    best_priority = min(priorities)
    return [
        index for index, priority in zip(indexes, priorities)
        if priority == best_priority
    ]


def _warehouse_row_priority(row, preferred_warehouses: list[str]) -> int:
    """Match the preferred Arabic warehouse name against the row's visible text."""
    if not preferred_warehouses:
        return 0
    return calculate_warehouse_priority_score(
        _warehouse_row_text(row), preferred_warehouses
    )


def _warehouse_row_text(row) -> str:
    try:
        return row.inner_text(timeout=1000)
    except PlaywrightError:
        logger.debug("tawreed_strategy.warehouse row name read failed")
        return ""


def _warehouse_row_discount(row) -> float:
    match = re.search(r"(-?\d+(?:[.,]\d+)?)\s*[%٪]", _warehouse_row_text(row))
    if not match:
        return -1.0
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return -1.0


def warehouse_row_quantity(row, available_quantity_selector: str) -> int:
    """Parse the numeric quantity from a warehouse row."""
    try:
        text = row.locator(available_quantity_selector).first.inner_text(
            timeout=1000
        ).strip()
    except PlaywrightError:
        logger.debug("tawreed_strategy.warehouse_row_quantity: row read failed")
        return 0
    try:
        return int(float(text.replace(",", "")))
    except (TypeError, ValueError):
        logger.debug("tawreed_strategy.warehouse_row_quantity: row quantity parse failed")
        return 0
