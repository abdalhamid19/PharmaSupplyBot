"""Query helper functions for manual review store."""

from __future__ import annotations

from typing import Iterable, Any

from .manual_review_hints import hint_key
from .manual_review_store_sql import SELECT_DECISIONS


def _unique_item_keys(items: Iterable[Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if isinstance(item, dict):
            code = item.get("code", "") or item.get("item_code", "")
            name = item.get("name", "") or item.get("item_name", "")
        else:
            code = getattr(item, "code", getattr(item, "item_code", ""))
            name = getattr(item, "name", getattr(item, "item_name", ""))
        key = hint_key(code, name)
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _chunks(values: list[tuple[str, str]], size: int):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _lookup_many_sql(keys: list[tuple[str, str]]) -> str:
    clauses = " or ".join("(item_code_key=%s and item_name_key=%s)" for _ in keys)
    return f"{SELECT_DECISIONS} where {clauses}"


def _flat_keys(keys: list[tuple[str, str]]) -> tuple[str, ...]:
    return tuple(value for key in keys for value in key)


__all__ = [
    "_unique_item_keys",
    "_chunks",
    "_lookup_many_sql",
    "_flat_keys",
]
