"""Products-page search and add-to-cart flow for Tawreed ordering."""

from __future__ import annotations

from contextlib import suppress
import re
import time
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
    DIALOG_MASK_SELECTOR,
    PRODUCT_ROWS_SELECTOR,
    QUANTITY_INPUT_SELECTOR,
    STORE_DETAILS_ENDPOINT,
)
from .tawreed_match_logs import write_match_log
from .tawreed_ui import (
    bounded_requested_quantity,
    cart_button,
    dialog_close_buttons,
    dialog_footer_buttons,
    fill_quantity_input,
    store_dialog_cart_buttons,
    store_dialog_rows,
    visible_dialog_masks,
    stores_button,
    visible_dialog,
)

MIN_SEARCH_QUERIES_PER_ITEM = 3
STORE_NAME_KEYS = (
    "storeName",
    "storeNameAr",
    "storeNameEn",
    "supplierName",
    "supplierNameAr",
    "supplierNameEn",
    "warehouseName",
    "warehouseNameAr",
    "warehouseNameEn",
    "pharmacyName",
    "branchName",
    "sellerName",
    "companyName",
)
NESTED_STORE_KEYS = ("store", "supplier", "warehouse", "pharmacy", "branch", "seller")
NESTED_NAME_KEYS = ("name", "nameAr", "nameEn", "arabicName", "englishName", "title")
DISCOUNT_KEYS = (
    "discountPercent",
    "discountPercentage",
    "discountRate",
    "discountValue",
    "discount",
    "cashDiscount",
    "companyDiscount",
    "offerDiscount",
    "pharmacyDiscount",
    "percentage",
    "percent",
)


def add_item_from_products_page(bot, page: Page, item: Item) -> None:
    """Add one item using the Tawreed products page search-and-store selection flow."""
    match, active_query = require_product_match(bot, page, item)
    row = matched_product_row(bot, page, match, active_query)
    open_add_to_cart_for_match(bot, page, row, item, match)


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search the products table and return the parsed API results for the query."""
    close_visible_dialogs(page)
    search = page.locator(bot.selectors.item_search_input).first
    search.click()
    search.fill("")
    search.fill(query)
    with suppress(Exception):
        page.wait_for_load_state("networkidle", timeout=1000)
    search.press("Enter")
    _wait_for_table_overlay_to_clear(page)
    wait_for_product_rows(page)
    if _table_has_no_results(page):
        return []
    return _dom_search_results(page, query)


def find_best_product_match(bot, page: Page, item: Item) -> tuple[MatchDecision, str | None]:
    """Search all candidate queries and return diagnostics plus the active query."""
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]] = []
    queries = _search_queries_for_item(item)
    for query_index, query in enumerate(queries):
        bot.last_searched_queries.append(query)
        results = search_products(bot, page, query)
        search_results_by_query.append((query, results))
        decision = _match_decision(bot, item, search_results_by_query)
        if _decisive_match(item, query, decision, query_index, len(queries)):
            write_match_log(bot, item, decision)
            return decision, query
        if _should_stop_after_no_results(queries, query_index, results):
            break
    active_query = search_results_by_query[-1][0] if search_results_by_query else None
    decision = _match_decision(bot, item, search_results_by_query)
    write_match_log(bot, item, decision)
    return decision, active_query


def require_product_match(bot, page: Page, item: Item) -> tuple[SearchMatch, str | None]:
    """Require a valid product match or raise a descriptive runtime error."""
    started_at = time.perf_counter()
    decision, active_query = find_best_product_match(bot, page, item)
    bot.last_match_elapsed_seconds = time.perf_counter() - started_at
    bot.last_match_decision = decision
    if decision.best_match:
        return decision.best_match, active_query
    raise bot.no_results_exception(
        f"No matching product found for '{item.name}' (code: {item.code})."
    )


def matched_product_row(bot, page: Page, match: SearchMatch, active_query: str | None):
    """Re-run the winning query and return the visible row that corresponds to the match."""
    if active_query != match.query:
        search_products(bot, page, match.query)
    _wait_for_table_overlay_to_clear(page)
    rows = visible_product_rows(page)
    row = _matched_row_by_signature(rows, match)
    if row is not None:
        return row
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
    try:
        text = row.inner_text()
    except Exception:
        return False
    normalized_text = " ".join(str(text).split())
    return (
        "No results found" in normalized_text
        or "لايوجد نتائج" in normalized_text
        or "لا يوجد نتائج" in normalized_text
    )


def wait_for_product_rows(page: Page) -> None:
    """Wait until the products table renders at least one visible row."""
    try:
        visible_product_rows(page).first.wait_for(timeout=2000)
    except Exception:
        pass
    if _table_has_no_results(page):
        return


def open_add_to_cart_for_match(bot, page: Page, row, item: Item, match: SearchMatch) -> None:
    """Open the add-to-cart dialog for the selected match and chosen store."""
    if match_has_multiple_stores(match):
        try:
            add_item_from_store_dialogs(bot, page, row, item)
            return
        except bot.skip_item_exception:
            raise
        except Exception:
            if not _row_cart_button_enabled(row):
                raise
            close_visible_dialogs(page)
    if _row_cart_button_enabled(row):
        click_single_store_cart(bot, row, item, match)
        bot.last_ordered_total_qty = fill_add_to_cart_dialog(bot, page, item.qty)
        return
    click_single_store_cart(bot, row, item, match)
    bot.last_ordered_total_qty = fill_add_to_cart_dialog(bot, page, item.qty)


def match_has_multiple_stores(match: SearchMatch) -> bool:
    """Return whether the matched product requires store selection first."""
    return int(match.data.get("productsCount") or 0) > 0


def open_store_cart_dialog(bot, page: Page, row) -> None:
    """Open the stores dialog and click the chosen store cart button."""
    store_rows = open_stores_dialog(bot, page, row)
    store_index, store = choose_next_store_for_remaining_quantity(
        store_rows,
        set(),
        warehouse_mode(bot),
        bot.skip_item_exception,
        minimum_discount_percent(bot),
    )
    record_selected_store(bot, store)
    stores_dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    store_dialog_cart_buttons(stores_dialog).nth(store_index).click()


def add_item_from_store_dialogs(bot, page: Page, row, item: Item) -> None:
    """Add the requested quantity across stores until fulfilled or supply is exhausted."""
    remaining_quantity = int(item.qty)
    used_store_ids: set[str] = set()
    selections: list[tuple[dict[str, Any], int]] = []
    while remaining_quantity > 0:
        store_rows = open_stores_dialog(bot, page, row)
        try:
            store_index, store = choose_next_store_for_remaining_quantity(
                store_rows,
                used_store_ids,
                warehouse_mode(bot),
                bot.skip_item_exception,
                minimum_discount_percent(bot),
            )
        except bot.skip_item_exception:
            close_visible_dialogs(page)
            if selections:
                break
            raise
        store_quantity = min(remaining_quantity, store_available_quantity(store))
        if store_quantity <= 0:
            close_visible_dialogs(page)
            break
        stores_dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
        store_dialog_cart_buttons(stores_dialog).nth(store_index).click()
        ordered_quantity = fill_add_to_cart_dialog(bot, page, store_quantity)
        selections.append((store, ordered_quantity))
        used_store_ids.add(store_identity(store, store_index))
        remaining_quantity -= ordered_quantity
    if not selections:
        raise bot.skip_item_exception("All available stores for this product are out of stock.")
    bot.last_ordered_total_qty = sum(quantity for _, quantity in selections)
    record_selected_stores(bot, selections)


def choose_next_store_for_remaining_quantity(
    stores: list[dict[str, Any]],
    used_store_ids: set[str],
    mode: str,
    skip_exception_cls: type[Exception],
    min_discount_percent: float = 0.0,
) -> tuple[int, dict[str, Any]]:
    """Return the next unused store to order from while splitting quantities."""
    choices = available_store_choices(stores, used_store_ids, min_discount_percent)
    if not choices:
        if min_discount_percent > 0:
            raise skip_exception_cls(
                f"No available stores meet the minimum discount {min_discount_percent:g}%."
            )
        raise skip_exception_cls("All available stores for this product are out of stock.")
    if mode == "first_available":
        return choices[0]
    if mode == "max_available":
        return max(choices, key=lambda choice: store_available_quantity(choice[1]))
    if mode == "max_discount":
        return max(
            choices,
            key=lambda choice: (
                store_discount_value(choice[1]),
                store_available_quantity(choice[1]),
            ),
        )
    raise ValueError(f"Unknown warehouse strategy mode: {mode}")


def available_store_choices(
    stores: list[dict[str, Any]],
    used_store_ids: set[str],
    min_discount_percent: float = 0.0,
) -> list[tuple[int, dict[str, Any]]]:
    """Return unused stores that still have available stock."""
    choices: list[tuple[int, dict[str, Any]]] = []
    for store_index, store in enumerate(stores):
        if store_identity(store, store_index) in used_store_ids:
            continue
        if store_available_quantity(store) <= 0:
            continue
        if not store_meets_minimum_discount(store, min_discount_percent):
            continue
        choices.append((store_index, store))
    return choices


def store_available_quantity(store: dict[str, Any]) -> int:
    """Return the available stock count for one Tawreed store row."""
    try:
        return int(float(store.get("availableQuantity") or 0))
    except Exception:
        return 0


def store_identity(store: dict[str, Any], fallback_index: int) -> str:
    """Return a stable identity for one store row while splitting quantities."""
    for key in ("storeProductId", "storeId", "supplierId", "warehouseId"):
        value = store.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return f"index:{fallback_index}"


def click_single_store_cart(bot, row, item: Item, match: SearchMatch) -> None:
    """Click the direct cart button for matches that do not require a stores dialog."""
    _wait_for_row_to_settle(row)
    available_quantity = int(match.data.get("availableQuantity") or 0)
    if available_quantity <= 0:
        raise bot.skip_item_exception(f"Matched product is out of stock for '{item.name}'.")
    min_discount = minimum_discount_percent(bot)
    if not store_meets_minimum_discount(match.data, min_discount):
        raise bot.skip_item_exception(
            f"Matched product discount is below the minimum discount {min_discount:g}%."
        )
    if not _row_cart_button_enabled(row):
        raise bot.skip_item_exception(_disabled_cart_reason(row, item.name))
    record_selected_store(bot, match.data)
    cart_button(row).click()


def record_selected_store(bot, store: dict[str, Any]) -> None:
    """Remember the selected Tawreed store details for the order summary report."""
    bot.last_selected_discount_percent = store_discount_percent(store)
    bot.last_selected_store_name = store_name(store)


def record_selected_stores(bot, selections: list[tuple[dict[str, Any], int]]) -> None:
    """Remember all selected stores for split-quantity order summary reporting."""
    bot.last_selected_discount_percent = " | ".join(
        selection_summary(store_discount_percent(store), quantity)
        for store, quantity in selections
    )
    bot.last_selected_store_name = " | ".join(
        selection_summary(store_name(store), quantity)
        for store, quantity in selections
    )


def selection_summary(value: str, quantity: int) -> str:
    """Return one compact selected-store summary cell value."""
    label = str(value or "").strip() or "unknown"
    return f"{label} (qty {quantity})"


def store_name(store: dict[str, Any]) -> str:
    """Return the display name for a Tawreed store/supplier payload."""
    direct_value = _first_text_field(store, STORE_NAME_KEYS)
    if direct_value:
        return direct_value
    if not _looks_like_product_payload(store):
        direct_name = _first_text_field(store, NESTED_NAME_KEYS)
        if direct_name:
            return direct_name
    nested_value = _first_nested_text_field(store, NESTED_STORE_KEYS, NESTED_NAME_KEYS)
    return nested_value


def store_discount_percent(store: dict[str, Any]) -> str:
    """Return the selected store discount as a human-readable percent value."""
    value = _first_discount_value(store)
    return _format_discount_percent(value)


def store_discount_value(store: dict[str, Any]) -> float:
    """Return the selected store discount as a comparable percent value."""
    return _discount_value_as_percent(_first_discount_value(store))


def minimum_discount_percent(bot) -> float:
    """Return the configured minimum discount percent for store selection."""
    try:
        return max(0.0, float(bot.config.warehouse_strategy.get("min_discount_percent") or 0))
    except Exception:
        return 0.0


def store_meets_minimum_discount(store: dict[str, Any], min_discount_percent: float) -> bool:
    """Return whether one store is allowed by the configured discount floor."""
    if min_discount_percent <= 0:
        return True
    return store_discount_value(store) >= min_discount_percent


def open_stores_dialog(bot, page: Page, row) -> list[dict[str, Any]]:
    """Open the stores dialog for a row and return the API payload behind it."""
    response_value, dialog_became_visible = _open_stores_dialog_with_response(bot, page, row)
    if response_value is not None:
        stores = _stores_from_payload(response_value.json())
        if stores:
            return stores
    if dialog_became_visible:
        return _stores_from_dialog_rows(page, bot)
    try:
        close_visible_dialogs(page)
    except Exception:
        pass
    raise RuntimeError("Stores dialog did not produce usable rows or API payload.")


def _open_stores_dialog_with_response(bot, page: Page, row):
    """Click the stores button while listening for Tawreed's store-details response."""
    dialog_became_visible = False
    try:
        with page.expect_response(
            lambda response: is_store_details_response(response),
            timeout=_search_response_timeout_ms(bot),
        ) as response_info:
            stores_button(row).click()
            dialog_became_visible = _stores_dialog_visible(page, bot)
        return _response_value(response_info), dialog_became_visible
    except Exception:
        return None, dialog_became_visible


def is_store_details_response(response) -> bool:
    """Return whether a network response belongs to the store-details endpoint."""
    return STORE_DETAILS_ENDPOINT in response.url and response.request.method == "POST"


def fill_add_to_cart_dialog(bot, page: Page, requested_qty: int) -> int:
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
        close_visible_dialogs(page)
        _wait_for_dialog_to_clear(page)
    return quantity


def warehouse_mode(bot) -> str:
    """Return the configured warehouse-selection mode."""
    return str(bot.config.warehouse_strategy.get("mode", "first_available"))


def close_visible_dialogs(page: Page) -> None:
    """Close any visible dialogs so later items can continue safely."""
    try:
        while visible_dialog_masks(page).count() > 0:
            dialog = visible_dialog(page, 1000)
            close_buttons = dialog_close_buttons(dialog)
            if close_buttons.count() > 0:
                close_buttons.first.click(force=True)
                dialog.wait_for(state="hidden", timeout=1500)
                continue
            try:
                visible_dialog_masks(page).last.click(force=True)
                dialog.wait_for(state="hidden", timeout=1500)
                continue
            except Exception:
                pass
            page.keyboard.press("Escape")
            dialog.wait_for(state="hidden", timeout=1500)
    except Exception:
        pass


def _stores_dialog_visible(page: Page, bot) -> bool:
    """Return whether the stores dialog became visible even without the API response."""
    try:
        dialog = visible_dialog(page, 2000)
        store_dialog_rows(dialog).first.wait_for(timeout=1500)
        return True
    except Exception:
        return False


def _stores_from_dialog_rows(page: Page, bot) -> list[dict[str, Any]]:
    """Return placeholder store rows based on visible dialog cart buttons."""
    dialog = visible_dialog(page, bot.config.runtime.timeout_ms)
    cart_buttons = store_dialog_cart_buttons(dialog)
    if cart_buttons.count() == 0:
        raise RuntimeError("Stores dialog became visible, but no cart buttons were found.")
    return [{"availableQuantity": 1} for _ in range(cart_buttons.count())]


def _stores_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized stores rows from a store-details payload."""
    return list(payload.get("data", []) or [])


def _first_text_field(source: dict[str, Any], keys: tuple[str, ...]) -> str:
    """Return the first non-empty string-like value for the provided keys."""
    for key in keys:
        value = source.get(key)
        if isinstance(value, (dict, list, tuple)):
            continue
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _first_nested_text_field(
    source: dict[str, Any],
    object_keys: tuple[str, ...],
    name_keys: tuple[str, ...],
) -> str:
    """Return the first non-empty nested store/supplier name value."""
    for object_key in object_keys:
        nested = source.get(object_key)
        if not isinstance(nested, dict):
            continue
        text = _first_text_field(nested, name_keys)
        if text:
            return text
    return ""


def _looks_like_product_payload(source: dict[str, Any]) -> bool:
    """Return whether the payload is a product row rather than a store row."""
    return any(key in source for key in ("productName", "productNameEn", "storeProductId"))


def _first_discount_value(source: dict[str, Any]) -> Any:
    """Return the first discount value found in a Tawreed payload."""
    for key in DISCOUNT_KEYS:
        if key not in source:
            continue
        value = source.get(key)
        if isinstance(value, dict):
            nested_value = _first_discount_value(value)
            if nested_value not in (None, ""):
                return nested_value
            continue
        if value not in (None, ""):
            return value
    for object_key in NESTED_STORE_KEYS:
        nested = source.get(object_key)
        if not isinstance(nested, dict):
            continue
        nested_value = _first_discount_value(nested)
        if nested_value not in (None, ""):
            return nested_value
    return ""


def _format_discount_percent(value: Any) -> str:
    """Format Tawreed discount values consistently for CSV/XLSX output."""
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        number_match = re.search(r"-?\d+(?:[.,]\d+)?", stripped)
        if not number_match:
            return stripped
        number = float(number_match.group(0).replace(",", "."))
        if "%" in stripped or "٪" in stripped:
            return f"{number:g}%"
        return _format_discount_number(number)
    try:
        return _format_discount_number(float(value))
    except Exception:
        return str(value).strip()


def _discount_value_as_percent(value: Any) -> float:
    """Return a numeric percent value for sorting discounts."""
    if value in (None, ""):
        return -1.0
    if isinstance(value, str):
        number_match = re.search(r"-?\d+(?:[.,]\d+)?", value.strip())
        if not number_match:
            return -1.0
        value = float(number_match.group(0).replace(",", "."))
    try:
        number = float(value)
    except Exception:
        return -1.0
    return number * 100 if 0 < number < 1 else number


def _format_discount_number(value: float) -> str:
    """Return a percent string, treating fractional values as rates."""
    percent = value * 100 if 0 < value < 1 else value
    return f"{percent:g}%"


def _response_value(response_info):
    """Return the resolved Playwright response when available."""
    if response_info is None:
        return None
    try:
        return response_info.value
    except Exception:
        return None


def _wait_for_dialog_to_clear(page: Page) -> None:
    """Wait briefly for remaining visible dialog masks to disappear."""
    try:
        page.locator(DIALOG_MASK_SELECTOR).first.wait_for(state="hidden", timeout=1500)
    except Exception:
        pass


def _search_response_timeout_ms(bot) -> int:
    """Return the shorter timeout used for search/store response waits."""
    return min(int(bot.config.runtime.timeout_ms), 1500)


def _dom_search_results(page: Page, query: str) -> list[dict[str, Any]]:
    """Build fallback product candidates from the visible products table rows."""
    results: list[dict[str, Any]] = []
    rows = visible_product_rows(page)
    for row_index in range(rows.count()):
        row = rows.nth(row_index)
        if is_no_results_row(row):
            continue
        candidate = _dom_candidate_from_row(row, query)
        if candidate:
            results.append(candidate)
    return results


def _table_has_no_results(page: Page) -> bool:
    """Return whether Tawreed's products table currently shows the no-results row."""
    rows = visible_product_rows(page)
    if rows.count() != 1:
        return False
    try:
        return is_no_results_row(rows.nth(0))
    except Exception:
        return False


def _dom_candidate_from_row(row, query: str) -> dict[str, Any] | None:
    """Return one fallback candidate parsed from a rendered products-table row."""
    name_lines = _row_name_lines(row)
    if not name_lines:
        return None
    if not _row_is_plausible_for_query(name_lines[0], query):
        return None
    supplier_count = _badge_int(row, "button:has(.pi-building) .p-badge")
    cart_count = _badge_int(row, "button:has(.pi-shopping-cart) .p-badge")
    return {
        "productNameEn": _dom_fallback_english_name(query, name_lines[0]),
        "productName": name_lines[0],
        "productsCount": supplier_count,
        "availableQuantity": max(cart_count, supplier_count, 1),
        "storeProductId": f"dom-row-{_normalized_dom_id(name_lines[0])}",
    }


def _row_name_lines(row) -> list[str]:
    """Return the visible product-name block lines for one rendered row."""
    try:
        name_block = row.locator("td").first.locator("div.flex.flex-column").first.inner_text().strip()
    except Exception:
        return []
    return [line.strip() for line in name_block.splitlines() if line.strip()]


def _badge_int(row, selector: str) -> int:
    """Return an integer badge value from the row or zero when absent."""
    try:
        text = row.locator(selector).first.inner_text().strip()
        return int(float(text))
    except Exception:
        return 0


def _normalized_dom_id(text: str) -> str:
    """Return a stable ASCII-ish identifier fragment for one DOM candidate."""
    return "".join(character if character.isalnum() else "-" for character in text)[:48]


def _dom_fallback_english_name(query: str, arabic_name: str) -> str:
    """Return a query-shaped fallback English name using numeric clues from the Arabic row."""
    query_tokens = [token for token in re.split(r"\s+", query.strip()) if token]
    non_numeric_tokens = [token for token in query_tokens if not any(ch.isdigit() for ch in token)]
    arabic_numeric_tokens = re.findall(r"\d+(?:\.\d+)?", arabic_name)
    return " ".join(non_numeric_tokens + arabic_numeric_tokens) or query


def _row_cart_button_enabled(row) -> bool:
    """Return whether the row's direct cart button is currently enabled."""
    try:
        return cart_button(row).is_enabled()
    except Exception:
        return False


def _disabled_cart_reason(row, item_name: str) -> str:
    """Return a more specific skip reason when the cart button is disabled."""
    visible_message = _row_unavailable_message(row)
    supplier_count = _badge_int(row, "button:has(.pi-building) .p-badge")
    cart_count = _badge_int(row, "button:has(.pi-shopping-cart) .p-badge")
    if visible_message:
        return f"Matched product is unavailable for '{item_name}': {visible_message}."
    if supplier_count <= 0 and cart_count <= 0:
        return f"Matched product has no available suppliers for '{item_name}'."
    return f"Matched product cart button is disabled for '{item_name}'."


def _row_unavailable_message(row) -> str:
    """Return the row's visible red status message when Tawreed shows one."""
    try:
        message = row.locator("div[style*='color: red']").first.inner_text().strip()
        return message
    except Exception:
        return ""


def _wait_for_table_overlay_to_clear(page: Page) -> None:
    """Wait briefly for Tawreed's table loading overlay to disappear after search updates."""
    try:
        page.locator(".p-datatable-loading-overlay").first.wait_for(state="hidden", timeout=2000)
    except Exception:
        pass


def _wait_for_row_to_settle(row) -> None:
    """Wait briefly for a matched row's cart button to stop changing before click."""
    try:
        cart_button(row).wait_for(timeout=1500)
    except Exception:
        pass


def _matched_row_by_signature(rows, match: SearchMatch):
    """Return the rendered row that best matches the chosen candidate signature."""
    target_signature = _candidate_signature(match.data)
    if not target_signature:
        return None
    for row_index in range(rows.count()):
        row = rows.nth(row_index)
        if is_no_results_row(row):
            continue
        if _row_signature(row) == target_signature:
            return row
    return None


def _candidate_signature(candidate: dict[str, Any]) -> str:
    """Return a stable normalized signature for a candidate's visible product text."""
    product_name = str(candidate.get("productName") or "")
    return _normalize_signature_text(product_name)


def _row_signature(row) -> str:
    """Return a stable normalized signature for a rendered row."""
    name_lines = _row_name_lines(row)
    if not name_lines:
        return ""
    return _normalize_signature_text(name_lines[0])


def _normalize_signature_text(text: str) -> str:
    """Return a compact comparable signature for visible row-name text."""
    return re.sub(r"\s+", " ", str(text or "").strip())


def _row_is_plausible_for_query(arabic_name: str, query: str) -> bool:
    """Return whether a DOM-only Arabic row is numerically plausible for the current query."""
    query_numbers = re.findall(r"\d+(?:\.\d+)?", query)
    if not query_numbers:
        return True
    row_numbers = re.findall(r"\d+(?:\.\d+)?", arabic_name)
    if not row_numbers:
        return False
    return bool(set(query_numbers) & set(row_numbers))


def _should_stop_after_no_results(
    queries: list[str],
    query_index: int,
    results: list[dict[str, Any]],
) -> bool:
    """Return whether repeated empty full-name searches should short-circuit later retries."""
    if results:
        return False
    if query_index < min(len(queries), MIN_SEARCH_QUERIES_PER_ITEM) - 1:
        return False
    if query_index >= 2:
        return True
    return len(queries) <= 1


def _match_decision(
    bot,
    item: Item,
    search_results_by_query: list[tuple[str, list[dict[str, Any]]]],
) -> MatchDecision:
    """Return the current best decision across all searched queries so far."""
    return explain_best_product_match(item, search_results_by_query, bot.config.matching)


def _decisive_match(
    item: Item,
    query: str,
    decision: MatchDecision,
    query_index: int,
    total_queries: int,
) -> bool:
    """Return whether the current best match is decisive enough to stop searching."""
    if query_index < min(total_queries, MIN_SEARCH_QUERIES_PER_ITEM) - 1:
        return False
    if not decision.best_match:
        return False
    if is_decisive_product_match(item.name or query, decision.best_match.data):
        return True
    best_diagnostic = _best_diagnostic_for_query(decision, query)
    if best_diagnostic is None or not best_diagnostic.accepted:
        return False
    if best_diagnostic.query != query:
        return False
    has_numeric_tokens = bool(re.findall(r"\d+(?:\.\d+)?", item.name or query))
    return bool(
        best_diagnostic.accepted_reason == "high_token_overlap"
        and best_diagnostic.breakdown.overlap_score >= 0.95
        and best_diagnostic.breakdown.sequence_score >= 0.8
        and (not has_numeric_tokens or best_diagnostic.breakdown.numeric_overlap >= 1.0)
    )


def _best_diagnostic_for_query(decision: MatchDecision, query: str):
    """Return the highest-ranked diagnostic produced by the active query."""
    matching = [diagnostic for diagnostic in decision.diagnostics if diagnostic.query == query]
    if not matching:
        return None
    return max(matching, key=lambda diagnostic: diagnostic.sort_key)
