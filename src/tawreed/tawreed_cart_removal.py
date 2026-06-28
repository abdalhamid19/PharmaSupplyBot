"""Tawreed cart item removal flow."""

from __future__ import annotations

from typing import Iterable

from playwright.sync_api import Page

from ..core.cart_removal_items import CartRemovalItem
from .tawreed_cart_removal_selectors import CartRemovalSelectors, CartRemovalTarget
from .tawreed_cart_removal_core import (
    remove_items_from_cart,
    _process_removal_target,
    _remove_matching_rows,
    remove_matching_cart_rows,
    _delete_cart_row,
)
from .tawreed_cart_removal_operations import (
    click_cart_delete_button,
    confirm_delete_if_needed,
    _visible_confirmation_dialog,
    _wait_after_cart_delete,
    _find_row_idx,
)
from .tawreed_cart_removal_helpers import (
    resolve_cart_removal_targets,
    _cart_stop_requested,
    _unique,
    _log,
)
from .tawreed_cart_removal_core import append_cart_removal_summary
from .tawreed_search_logic import require_product_match


__all__ = [
    "CartRemovalSelectors",
    "CartRemovalTarget",
    "remove_items_from_cart",
    "resolve_cart_removal_targets",
    "remove_matching_cart_rows",
    "click_cart_delete_button",
    "confirm_delete_if_needed",
    "append_cart_removal_summary",
    "require_product_match",
]
