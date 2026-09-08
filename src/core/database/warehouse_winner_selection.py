"""Deterministic purchase-price comparison, independent of ordering choices."""

from __future__ import annotations

import math
import re
from typing import Any

RULE_VERSION = 1
DEFAULT_CURRENCY = "EGP"
PREFERRED_WAREHOUSES = (
    "شركه البركه (الجيزه)",
    "شركه الماسه (مالك سابقا ) (الجيزه)",
    "شركه الشفاء ميدكو - الريحان سابقا (الجيزه)",
    "شركه الفا فارما (الجيزه)",
    "شركه مصر مديكال (الجيزه)",
    "شركه نيو سيدرا (القليوبيه)",
    "شركه الريان (القاهره)",
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


def _priority(row: dict[str, Any]) -> tuple:
    name = warehouse_display_name(row)
    preferred = [normalized_name(value) for value in PREFERRED_WAREHOUSES]
    normalized = normalized_name(name)
    rank = preferred.index(normalized) if normalized in preferred else len(preferred)
    return (
        0 if source_kind(row.get("source", "")) == "excel-target" else 1,
        rank, name.casefold(), row["store_key"], row["store_product_id"],
    )


def warehouse_display_name(row: dict[str, Any]) -> str:
    """Show the catalog filename while retaining its full identity elsewhere."""
    name = row.get("store_name") or row.get("source_label") or ""
    if source_kind(row.get("source", "")) == "excel-target":
        return name.split("@", 1)[-1].removeprefix("excel-target:")
    return name


def select_warehouse_winner(offers: list[dict[str, Any]]) -> tuple[dict | None, str]:
    """Return one available cheapest offer, or an explicit exclusion reason."""
    eligible = _eligible_offers(offers)
    if not eligible:
        return None, "no_eligible_offer"
    if len({currency_code(row.get("currency")) for row in eligible}) > 1:
        return None, "mixed_currencies"
    price = min(float(row["purchase_price"]) for row in eligible)
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
