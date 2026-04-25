"""Shared Tawreed URLs, selectors, labels, and endpoint fragments."""

from __future__ import annotations


PRODUCTS_PAGE_ROUTE = "#/catalog/store-products/dv/"
PRODUCT_ROWS_SELECTOR = "tbody.p-datatable-tbody > tr"
PRODUCT_SEARCH_ENDPOINT = "stores/products/search/similar5"
STORE_DETAILS_ENDPOINT = "stores/products/product/get"
VISIBLE_DIALOG_SELECTOR = ".p-dialog:visible"
DIALOG_FOOTER_BUTTONS_SELECTOR = ".p-dialog-footer button"
QUANTITY_INPUT_SELECTOR = "input[role='spinbutton']"
STORES_BUTTON_SELECTOR = "button:has(.pi-building)"
CART_BUTTON_SELECTOR = "button:has(.pi-shopping-cart)"
STORE_DIALOG_CART_BUTTONS_SELECTOR = ".p-dialog-content button:has(.pi-shopping-cart)"
ENABLED_CHECKOUT_TEXT_SELECTOR = "button:has-text('Checkout'):not([disabled])"
CHECKOUT_CONFIRMATION_LABELS = (
    "Confirm",
    "confirm",
    "Ok",
    "OK",
    "Continue",
    "Yes",
    "Submit",
    "Ã˜ÂªÃ˜Â£Ã™Æ’Ã™Å Ã˜Â¯",
    "Ã™â€¦Ã˜ÂªÃ˜Â§Ã˜Â¨Ã˜Â¹Ã˜Â©",
    "Ã™â€ Ã˜Â¹Ã™â€¦",
)
