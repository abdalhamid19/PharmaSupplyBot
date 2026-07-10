"""Selected-store artifact field helpers."""

from __future__ import annotations

import re


_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_QTY_SUFFIX_RE = re.compile(r"\s*\(\s*qty\s+([^)]*)\)\s*$", re.IGNORECASE)


def selected_store_discount_fields(store_name: str, discount: str) -> dict[str, object]:
    """Return selected store/discount fields with split multi-store columns."""
    fields: dict[str, object] = {
        "selected_store_name": store_name,
        "selected_discount_percent": discount,
    }
    pairs = _sorted_selection_pairs(store_name, discount)
    if len(pairs) <= 1:
        return fields
    for index, (current_store, current_discount, quantity) in enumerate(pairs, start=1):
        fields[f"selected_store_name_{index}"] = current_store
        fields[f"selected_discount_percent_{index}"] = current_discount
        fields[f"selected_qty_{index}"] = quantity
    return fields


def _sorted_selection_pairs(store_name: str, discount: str) -> list[tuple[str, str, str]]:
    stores = _split_selection_values(store_name)
    discounts = _split_selection_values(discount)
    count = max(len(stores), len(discounts))
    pairs = [_selection_pair(stores, discounts, index) for index in range(count)]
    return sorted(pairs, key=lambda pair: _discount_sort_value(pair[1]), reverse=True)


def _selection_pair(
    stores: list[str], discounts: list[str], index: int
) -> tuple[str, str, str]:
    store, store_qty = _strip_qty(stores[index] if index < len(stores) else "")
    discount, discount_qty = _strip_qty(
        discounts[index] if index < len(discounts) else ""
    )
    return store, discount, store_qty or discount_qty


def _split_selection_values(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def _strip_qty(value: str) -> tuple[str, str]:
    match = _QTY_SUFFIX_RE.search(value)
    if not match:
        return value.strip(), ""
    return value[: match.start()].strip(), match.group(1).strip()


def _discount_sort_value(value: str) -> float:
    match = _NUMBER_RE.search(str(value or ""))
    if not match:
        return -1.0
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return -1.0


__all__ = ["selected_store_discount_fields"]
