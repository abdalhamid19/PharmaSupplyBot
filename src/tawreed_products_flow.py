"""Products-page search and add-to-cart flow for Tawreed ordering."""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from .excel import Item
from .matching_models import MatchDecision, SearchMatch
from .product_matching import (
    _search_queries_for_item,
    explain_best_product_match,
    is_decisive_product_match,
)
from .tawreed_constants import (
    PRODUCT_ROWS_SELECTOR,
    PRODUCT_SEARCH_ENDPOINT,
    QUANTITY_INPUT_SELECTOR,
    STORE_DETAILS_ENDPOINT,
)
from .tawreed_match_logs import write_match_log
from .tawreed_strategy import choose_store_index
from .tawreed_ui import (
    bounded_requested_quantity,
    cart_button,
    dialog_footer_buttons,
    fill_quantity_input,
    store_dialog_cart_buttons,
    stores_button,
    visible_dialog,
)


def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    match, active_query = require_product_match(bot, page, item)
    row = matched_product_row(bot, page, match, active_query)
    open_add_to_cart_for_match(bot, page, row, item, match)
    fill_add_to_cart_dialog(bot, page, item.qty)


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the products table and return the parsed API results for the query."""
    search = page.locator(bot.selectors.item_search_input).first
    search.click()
    search.fill("")
    search.fill(query)
    with page.expect_response(
        is_product_search_response,
        timeout=bot.config.runtime.timeout_ms,
    ) as response_info:
        search.press("Enter")
    payload = response_info.value.json()
    wait_for_product_rows(page)
    return list(payload.get("data", {}).get("content", []) or [])


def find_best_product_match(bot, page: Page, item: Item) -> tuple[MatchDecision, str | None]:
    """Search all candidate queries and return diagnostics plus the active query."""
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]] = []
    for query in _search_queries_for_item(item):
        results = search_products(bot, page, query)
        search_results_by_query.append((query, results))
        decision = _match_decision(bot, item, search_results_by_query)
        if _decisive_match(item, query, decision):
            write_match_log(bot, item, decision)
            return decision, query
    active_query = search_results_by_query[-1][0] if search_results_by_query else None
    decision = _match_decision(bot, item, search_results_by_query)
    write_match_log(bot, item, decision)
    return decision, active_query


def require_product_match(bot, page: Page, item: Item) -> tuple[SearchMatch, str | None]:
    """Require a valid product match or raise a descriptive runtime error."""
    decision, active_query = find_best_product_match(bot, page, item)
    if decision.best_match:
        return decision.best_match, active_query
    raise RuntimeError(f"No matching product found for '{item.name}' (code: {item.code}).")


def matched_product_row(bot, page: Page, match: SearchMatch, active_query: str | None):
    """Re-run the winning query and return the visible row that corresponds to the match."""
    if active_query != match.query:
        search_products(bot, page, match.query)
    rows = visible_product_rows(page)
    if rows.count() <= match.row_index:
        raise RuntimeError(missing_row_message(match))
    row = rows.nth(match.row_index)
    if is_no_results_row(row):
        raise RuntimeError(f"No results found for '{match.query}'.")
    return row


def visible_product_rows(page: Page):
    """Return the rendered product rows in the current products table."""
    return page.locator(PRODUCT_ROWS_SELECTOR)


def missing_row_message(match: SearchMatch) -> str:
    """Build the error shown when a matched row disappears from the rendered table."""
    return (
        f"Matched row index {match.row_index} is not visible after searching for "
        f"'{match.query}'."
    )


def is_no_results_row(row) -> bool:
    """Return whether the current table row is Tawreed's no-results placeholder."""
    return "No results found" in row.inner_text()


def wait_for_product_rows(page: Page) -> None:
    """Wait until the products table renders at least one visible row."""
    try:
        visible_product_rows(page).first.wait_for(timeout=2000)
    except Exception:
        pass


def open_add_to_cart_for_match(bot, page: Page, row, item: Item, match: SearchMatch) -> None:
    """Open the add-to-cart dialog for the selected match and chosen store."""
    if match_has_multiple_stores(match):
        open_store_cart_dialog(bot, page, row)
        return
    click_single_store_cart(row, item, match, bot.skip_item_exception)


def match_has_multiple_stores(match: SearchMatch) -> bool:
    """Return whether the matched product requires store selection first."""
    return int(match.data.get("productsCount") or 0) > 0


def open_store_cart_dialog(bot, page: Page, row) -> None:
    """Open the stores dialog and click the chosen store cart button."""
    store_rows = open_stores_dialog(bot, page, row)
    store_index = choose_store_index(
        store_rows,
        warehouse_mode(bot),
        bot.skip_item_exception,
    )
    stores_dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    store_dialog_cart_buttons(stores_dialog).nth(store_index).click()


def click_single_store_cart(row, item: Item, match: SearchMatch, skip_item_exception) -> None:
    """Click the direct cart button for matches that do not require a stores dialog."""
    available_quantity = int(match.data.get("availableQuantity") or 0)
    if available_quantity <= 0:
        raise skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
    cart_button(row).click()


def is_product_search_response(response) -> bool:
    """Return whether a network response belongs to the product search endpoint."""
    return PRODUCT_SEARCH_ENDPOINT in response.url and response.request.method == "POST"


def open_stores_dialog(bot, page: Page, row) -> list[dict[str, Any]]:
    """Open the stores dialog for a row and return the API payload behind it."""
    with page.expect_response(
        lambda response: is_store_details_response(response),
        timeout=bot.config.runtime.timeout_ms,
    ) as response_info:
        stores_button(row).click()
    payload = response_info.value.json()
    stores = list(payload.get("data", []) or [])
    if not stores:
        raise RuntimeError("Stores dialog opened, but no store rows were returned.")
    return stores


def is_store_details_response(response) -> bool:
    """Return whether a network response belongs to the store-details endpoint."""
    return STORE_DETAILS_ENDPOINT in response.url and response.request.method == "POST"


def fill_add_to_cart_dialog(bot, page: Page, requested_qty: int) -> None:
    """Fill the quantity dialog and submit the add-to-cart action."""
    dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    footer_buttons = dialog_footer_buttons(dialog, bot.config.runtime.timeout_ms)
    quantity_input = dialog.locator(QUANTITY_INPUT_SELECTOR).first
    quantity = bounded_requested_quantity(quantity_input, requested_qty)
    fill_quantity_input(quantity_input, quantity)
    footer_buttons.last.click()
    try:
        dialog.wait_for(state="hidden", timeout=1500)
    except Exception:
        pass


def warehouse_mode(bot) -> str:
    """Return the configured warehouse-selection mode."""
    return str(bot.config.warehouse_strategy.get("mode", "first_available"))


def _match_decision(
    bot,
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> MatchDecision:
    """Return the current best decision across all searched queries so far."""
    return explain_best_product_match(item, search_results_by_query, bot.config.matching)


def _decisive_match(item: Item, query: str, decision: MatchDecision) -> bool:
    """Return whether the current best match is decisive enough to stop searching."""
    return bool(
        decision.best_match
        and is_decisive_product_match(item.name or query, decision.best_match.data)
    )
