"""Deterministic purchase-price comparison, independent of ordering choices."""

from __future__ import annotations

import math
import re
from typing import Any

RULE_VERSION = 2
DEFAULT_CURRENCY = "EGP"
PURCHASE_PRICE_TOLERANCE = 1.0
PREFERRED_WAREHOUSES = (
    "شركه البركه (الجيزه)",
    "شركه الماسه (مالك سابقا ) (الجيزه)",
    "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)",
    "شركه الفا فارما (الجيزه)",
    "شركه الريان (القاهره)",
    "شركه ابو عميره (الجيزه)",
    "شركه الادهم (الجيزه)",
    "شركه التحرير (الجيزه)",
)


def normalized_name(value: str) -> str:
    """Ignore spelling decoration and whitespace, not warehouse branches."""
    value = value.translate(str.maketrans("أإآىة", "ااايه"))
    return re.sub(r"[\W_]+", "", value).casefold()


def source_kind(value: str) -> str:
    """Collapse the historical snapshot source aliases."""
    return "excel-target" if value in {"excel_target", "excel-target"} else "tawreed"


def currency_code(value: str) -> str:
    """The Egyptian ordering flow has no configurable run currency."""
    text = (value or "").strip().upper()
    aliases = {"", "EGP", "LE", "L.E.", "ج.م", "جنيه", "جنيه مصري"}
    return DEFAULT_CURRENCY if text in aliases else text


def warehouse_priority_rank(
    row: dict[str, Any], preferred_warehouses: tuple[str, ...] | list[str] | None = None
) -> int:
    """Return the configured Tawreed warehouse priority rank."""
    name = warehouse_display_name(row)
    preferred = preferred_warehouses or PREFERRED_WAREHOUSES
    return _warehouse_rank(name, preferred)


def purchase_prices_are_tied(first: float, second: float) -> bool:
    """Return whether two purchase prices differ by less than one EGP."""
    return abs(float(first) - float(second)) < PURCHASE_PRICE_TOLERANCE


def _priority(row: dict[str, Any]) -> tuple:
    name = warehouse_display_name(row)
    kind = source_kind(row.get("source", ""))
    rank = warehouse_priority_rank(row) if kind == "tawreed" else 0
    return (
        0 if kind == "excel-target" else 1,
        rank,
        name.casefold(),
        row["store_key"],
        row["store_product_id"],
    )


def _warehouse_rank(
    name: str, preferred_warehouses: tuple[str, ...] | list[str]
) -> int:
    preferred = [normalized_name(value) for value in preferred_warehouses]
    normalized = normalized_name(name)
    for rank, preferred_name in enumerate(preferred):
        matches = (
            normalized == preferred_name
            or normalized in preferred_name
            or preferred_name in normalized
        )
        if matches:
            return rank
    return len(preferred)


def warehouse_display_name(row: dict[str, Any]) -> str:
    """Show the catalog filename while retaining its full identity elsewhere."""
    name = row.get("store_name") or row.get("source_label") or row.get("store_key") or ""
    if source_kind(row.get("source", "")) == "excel-target":
        return name.split("@", 1)[-1].removeprefix("excel-target:")
    return name


def select_warehouse_winner(offers: list[dict[str, Any]]) -> tuple[dict | None, str]:
    """Return one available lowest-price offer, or an exclusion reason."""
    eligible = _eligible_offers(offers)
    if not eligible:
        return None, "no_eligible_offer"
    if len({currency_code(row.get("currency")) for row in eligible}) > 1:
        return None, "mixed_currencies"
    price = min(float(row["purchase_price"]) for row in eligible)
    same_source = {source_kind(row.get("source", "")) for row in eligible}
    if same_source == {"tawreed"}:
        tied = [
            row for row in eligible
            if purchase_prices_are_tied(float(row["purchase_price"]), price)
        ]
    else:
        tied = [row for row in eligible if float(row["purchase_price"]) == price]
    winner = min(tied, key=_priority)
    return winner, _selection_reason(tied, winner)


def _eligible_offers(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = []
    for row in offers:
        try:
            price = float(row["purchase_price"])
            available = float(row["available_qty"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(price) and price > 0 and math.isfinite(available) and available > 0:
            eligible.append(row)
    return eligible


def _selection_reason(tied: list[dict], winner: dict) -> str:
    reason = "lowest_purchase_price"
    if len(tied) > 1:
        priorities = {_priority(row)[0] for row in tied}
        ranks = {_priority(row)[1] for row in tied}
        if len(priorities) > 1:
            reason = "excel_preferred"
        elif _priority(winner)[0] == 1 and len(ranks) > 1:
            reason = "preferred_warehouse"
        else:
            reason = "stable_name_identity"
    return reason
