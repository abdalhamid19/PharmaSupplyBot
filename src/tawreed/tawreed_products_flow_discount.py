"""Discount and warehouse strategy helpers for Tawreed products flow."""

from typing import Any

from .tawreed_pricing import discount_value_as_percent, first_discount_value


def _wh_mode(bot):
    return bot.config.warehouse_strategy.get("mode", "first_available")


def _min_disc(bot):
    return float(bot.config.warehouse_strategy.get("min_discount_percent", 0))


def _preferred_warehouses(bot) -> list[str]:
    return bot.config.warehouse_strategy.get("preferred_warehouses", [])


def _find_max_discount(stores: list[dict[str, Any]]) -> float:
    """Find the maximum discount percent among available stores."""
    max_discount = 0.0
    for store in stores:
        if int(store.get("availableQuantity", 0) or 0) > 0:
            discount = discount_value_as_percent(first_discount_value(store))
            max_discount = max(max_discount, discount)
    return max_discount


def _effective_min_discount(bot, sels) -> float:
    if _wh_mode(bot) != "max_discount" or not sels:
        return _min_disc(bot)
    return max(_min_disc(bot), _selected_max_discount(sels))


def _selected_max_discount(sels) -> float:
    return max(
        discount_value_as_percent(first_discount_value(store)) for store, _ in sels
    )
