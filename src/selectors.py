"""Selector configuration helpers for Tawreed Playwright automation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_models import AppConfig
from .tawreed_constants import (
    CART_CONFIRM_DELETE_BUTTON_SELECTOR,
    CART_DELETE_BUTTON_SELECTOR,
    CARTS_PAGE_ROUTE,
    PRODUCT_ROWS_SELECTOR,
)


LOGIN_DEFAULTS = {
    "login_email": ("login", "email_input", "input[type='email']"),
    "login_password": ("login", "password_input", "input[type='password']"),
    "login_submit": ("login", "submit_button", "button[type='submit']"),
    "logged_in_marker": ("nav", "logged_in_marker", "text=Home"),
}

ORDER_FLOW_DEFAULTS = {
    "go_to_orders": ("order_flow", "go_to_orders", "text=Orders"),
    "new_order": ("order_flow", "new_order", "text=New Order"),
    "item_search_input": ("order_flow", "item_search_input", "input[placeholder*='Search']"),
    "item_first_result": ("order_flow", "item_first_result", ":nth-match(.results *, 1)"),
    "qty_input": ("order_flow", "qty_input", "input[type='number']"),
    "add_item_button": ("order_flow", "add_item_button", "text=Add"),
    "confirm_order_button": ("order_flow", "confirm_order_button", "text=Confirm"),
}

CART_FLOW_DEFAULTS = {
    "cart_route": ("cart_flow", "route", CARTS_PAGE_ROUTE),
    "cart_rows": ("cart_flow", "rows", PRODUCT_ROWS_SELECTOR),
    "cart_delete_button": ("cart_flow", "delete_button", CART_DELETE_BUTTON_SELECTOR),
    "cart_confirm_delete_button": (
        "cart_flow",
        "confirm_delete_button",
        CART_CONFIRM_DELETE_BUTTON_SELECTOR,
    ),
}

WAREHOUSE_DEFAULTS = {
    "warehouse_rows": ("warehouse_rows", ".warehouse-row"),
    "warehouse_available_qty": ("available_qty", ".available"),
    "warehouse_pick_button": ("pick_button", "text=Select"),
}


@dataclass(frozen=True)
class _Sel:
    """Resolved selectors used by Tawreed Playwright automation flows."""

    login_email: str
    login_password: str
    login_submit: str
    logged_in_marker: str
    go_to_orders: str
    new_order: str
    item_search_input: str
    item_first_result: str
    qty_input: str
    add_item_button: str
    confirm_order_button: str
    cart_route: str
    cart_rows: str
    cart_delete_button: str
    cart_confirm_delete_button: str
    warehouse_rows: str
    warehouse_available_qty: str
    warehouse_pick_button: str


def _get(values: dict[str, Any], *keys: str, default: str = "") -> str:
    """Read a nested selector key and return a string fallback when it is absent."""
    current: Any = values
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return str(current)


def _selectors(config: AppConfig) -> _Sel:
    """Build the selector dataclass from configuration with safe defaults."""
    selectors_config = config.selectors
    warehouse_selectors = _warehouse_selectors(config)
    selector_values = {
        **_mapped_selectors(selectors_config, LOGIN_DEFAULTS),
        **_mapped_selectors(selectors_config, ORDER_FLOW_DEFAULTS),
        **_mapped_selectors(selectors_config, CART_FLOW_DEFAULTS),
        **_warehouse_selector_values(warehouse_selectors),
    }
    return _Sel(**selector_values)


def _warehouse_selectors(config: AppConfig) -> dict[str, Any]:
    """Return the warehouse selector section from config when present."""
    if isinstance(config.warehouse_strategy, dict):
        return dict(config.warehouse_strategy.get("selectors", {}))
    return {}


def _mapped_selectors(
    selectors_config: dict[str, Any],
    selector_defaults: dict[str, tuple[str, str, str]],
) -> dict[str, str]:
    """Resolve a selector group from nested config values and defaults."""
    return {
        field_name: _get(selectors_config, section, key, default=default_value)
        for field_name, (section, key, default_value) in selector_defaults.items()
    }


def _warehouse_selector_values(warehouse_selectors: dict[str, Any]) -> dict[str, str]:
    """Resolve warehouse-related selectors from config values and defaults."""
    return {
        field_name: str(warehouse_selectors.get(key, default_value))
        for field_name, (key, default_value) in WAREHOUSE_DEFAULTS.items()
    }
