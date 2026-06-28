"""Products-page search and add-to-cart flow for Tawreed ordering."""

from .tawreed_products_flow_main import (
    add_item_from_products_page,
    matched_product_row,
    open_add_to_cart_for_match,
)
from .tawreed_products_flow_stores import (
    add_item_from_store_dialogs,
    open_stores_dialog,
    _click_cart,
)
from .tawreed_products_flow_search import (
    search_visible_products_table,
)
from .tawreed_products_flow_discount import (
    _effective_min_discount,
    _find_max_discount,
)
from .tawreed_ui import cart_button, visible_dialog, visible_product_rows, store_dialog_cart_buttons
from .tawreed_waits import wait_for_table_overlay_to_clear, wait_for_row_to_settle
from .tawreed_products_flow_dialog import fill_add_to_cart_dialog
from .tawreed_products_flow_search import _matched_row_by_sig

__all__ = [
    "add_item_from_products_page",
    "matched_product_row",
    "open_add_to_cart_for_match",
    "add_item_from_store_dialogs",
    "open_stores_dialog",
    "search_visible_products_table",
    "_click_cart",
    "_effective_min_discount",
    "_find_max_discount",
    "cart_button",
    "visible_dialog",
    "wait_for_table_overlay_to_clear",
    "visible_product_rows",
    "store_dialog_cart_buttons",
    "wait_for_row_to_settle",
    "fill_add_to_cart_dialog",
    "_matched_row_by_sig",
]
