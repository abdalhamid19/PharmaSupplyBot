"""DOM-backed Tawreed product table search helpers."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

from ..tawreed_constants import (
    NESTED_NAME_KEYS,
    NESTED_STORE_KEYS,
    PRODUCT_SEARCH_ENDPOINT,
    STORE_NAME_KEYS,
)
from .tawreed_product_search_select import has_orderable_candidate, select_search_candidates
from ..matching.tawreed_timing import record_timing

PRODUCT_SEARCH_INPUT_SELECTOR = (
    "#tawreedTableGlobalSearch, "
    "input[name='tawreedTableGlobalSearch'], "
    "input[type='search'], "
    "input[placeholder*='بحث'], "
    "input[placeholder*='Search']"
)
_PRODUCT_LIST_KEYS = ("data", "content", "items", "products", "result", "results", "storeProducts")


def search_products(bot, page: Page, query: str) -> list[dict[str, Any]]:
    """Search products and prefer API candidates over DOM fallbacks."""
    bot.log(f"Searching for '{query}'...")
    api_candidates = _execute_api_search(bot, page, query)
    
    if api_candidates is not None and has_orderable_candidate(api_candidates):
        return api_candidates
    
    return _execute_dom_fallback(bot, page, query, api_candidates)


def _execute_api_search(bot, page, query):
    from ..tawreed_dialogs import close_visible_dialogs
    started_at = time.perf_counter()
    close_visible_dialogs(page)
    record_timing(bot, "dialog_close_seconds", time.perf_counter() - started_at)
    started_at = time.perf_counter()
    api_candidates = _submit_product_search_with_api(page, query)
    record_timing(bot, "api_search_seconds", time.perf_counter() - started_at)
    return api_candidates


def _execute_dom_fallback(bot, page, query, api_candidates):
    from ..tawreed_dom import dom_search_results
    from ..tawreed_ui import is_no_results_row
    from ..matching.tawreed_timing import wait_for_table_overlay_to_clear

    started_at = time.perf_counter()
    wait_for_table_overlay_to_clear(page)
    rows = _ready_product_rows(page)
    record_timing(bot, "dom_wait_seconds", time.perf_counter() - started_at)
    if rows is None or is_no_results_row(rows.first):
        return select_search_candidates(api_candidates, [])
    return select_search_candidates(api_candidates, dom_search_results(page, query))


def _submit_product_search_with_api(page: Page, query: str) -> list[dict[str, Any]] | None:
    try:
        pattern = _search_response_pattern()
        with page.expect_response(pattern, timeout=2000) as resp:
            _submit_product_search(page, query)
        return _api_candidates(resp.value.json())
    except Exception:
        return None

def _search_response_pattern():
    return re.compile(f".*{PRODUCT_SEARCH_ENDPOINT}.*")

def _api_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = _product_dicts(payload)
    return [_enrich_candidate_with_company(c) for c in candidates]


def _product_dicts(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if _is_product_dict(item)]
    if not isinstance(value, dict):
        return []
    if _is_product_dict(value):
        return [value]
    return _first_nested_product_list(value)


def _first_nested_product_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in _PRODUCT_LIST_KEYS:
        candidates = _product_dicts(payload.get(key))
        if candidates:
            return candidates
    return []


def _is_product_dict(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get("productName") or value.get("productNameEn"))


def _enrich_candidate_with_company(candidate: dict[str, Any]) -> dict[str, Any]:
    """Add companyName field from nested store/supplier objects if missing."""
    if candidate.get("companyName"):
        return candidate
    company = _extract_company_name(candidate)
    if company:
        candidate["companyName"] = company
    return candidate


def _extract_company_name(source: dict[str, Any]) -> str:
    """Extract company name using STORE_NAME_KEYS and nested objects."""
    for key in STORE_NAME_KEYS:
        value = str(source.get(key) or "").strip()
        if value:
            return value
    for obj_key in NESTED_STORE_KEYS:
        nested = source.get(obj_key)
        if isinstance(nested, dict):
            for name_key in NESTED_NAME_KEYS:
                value = str(nested.get(name_key) or "").strip()
                if value:
                    return value
    return ""


def _submit_product_search(page: Page, query: str) -> None:
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    search.fill(query)
    search.press("Enter")


def _ready_product_rows(page: Page):
    from ..tawreed_ui import visible_product_rows
    rows = visible_product_rows(page)
    try:
        rows.first.wait_for(timeout=1500)
    except Exception:
        return None
    return rows if rows.count() > 0 else None
