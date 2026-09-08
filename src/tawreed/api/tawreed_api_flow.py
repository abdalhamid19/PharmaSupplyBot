"""Public API-backed Tawreed execution flows."""

from __future__ import annotations

from .tawreed_api_match_only_metadata import (
    api_match_only_store_choice,
    record_api_match_only_store_metadata,
)

# Re-export from split modules
from .tawreed_api_flow_cart import _submit_order_if_enabled
from .tawreed_api_flow_main import (
    match_items_only_with_api,
    place_order_with_api,
    remove_cart_items_with_api,
)
from .tawreed_api_flow_matching import require_api_match


__all__ = [
    "match_items_only_with_api",
    "record_api_match_only_store_metadata",
    "api_match_only_store_choice",
    "place_order_with_api",
    "remove_cart_items_with_api",
    "require_api_match",
    # Legacy callers still import this helper from the facade.
    "_submit_order_if_enabled",
]
