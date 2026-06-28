"""Utility functions for Tawreed API flow (deprecated - functionality moved to tawreed_api_flow.py)."""

import time
from typing import Iterable

from .tawreed_api_client import TawreedApiClient
from .tawreed_api_flow import _require_contract, _warm_up_api_client


def remove_cart_items_with_api(bot, items: Iterable[object]) -> None:
    """Remove requested cart items through discovered API endpoints (deprecated)."""
    from .tawreed_api_flow import remove_cart_items_with_api as _remove_cart_items_with_api
    _remove_cart_items_with_api(bot, items)


def _submit_order_if_enabled(bot, api: TawreedApiClient, added_any: bool) -> None:
    """Submit order if enabled (deprecated)."""
    from .tawreed_api_flow import _submit_order_if_enabled as _submit_order_if_enabled_impl
    _submit_order_if_enabled_impl(bot, api, added_any)


def _require_contract(api: TawreedApiClient, *fields: str) -> None:
    """Require contract (deprecated)."""
    from .tawreed_api_flow import _require_contract as _require_contract_impl
    _require_contract_impl(api, *fields)


def _warm_up_api_client(bot, api: TawreedApiClient) -> None:
    """Warm up API client (deprecated)."""
    from .tawreed_api_flow import _warm_up_api_client as _warm_up_api_client_impl
    _warm_up_api_client_impl(bot, api)
