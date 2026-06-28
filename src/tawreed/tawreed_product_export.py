"""Tawreed product catalog export - merged module."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

from openpyxl import Workbook
from playwright.sync_api import Page, Response

from .product_export_deduplicator import (
    count_duplicates_removed,
    deduplicate_products,
)
from .tawreed_constants import PRODUCT_SEARCH_ENDPOINT
from .tawreed_product_search import (
    PRODUCT_SEARCH_INPUT_SELECTOR,
    _api_candidates,
    _search_response_pattern,
)

# ============================================================================
# Constants and Initialization
# ============================================================================

# From tawreed_product_export_api.py
DEFAULT_EXPORT_PAGE_SIZE = 100
DEFAULT_EXPORT_STEM = "tawreed_products"
EXPORT_REQUEST_BODY = {"mode": "error", "langCode": "ar", "data": {"displayType": 1}}

# From tawreed_product_export_searches.py
ENGLISH_EXPORT_SEARCH_TERMS = tuple(
    chr(code) for code in range(ord("A"), ord("Z") + 1)
)
ARABIC_EXPORT_SEARCH_TERMS = (
    "ا", "أ", "إ", "آ", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر",
    "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق", "ك", "ل",
    "م", "ن", "ه", "ة", "و", "ي", "ى",
)
EXPORT_SEARCH_TERMS = ("",) + ENGLISH_EXPORT_SEARCH_TERMS + ARABIC_EXPORT_SEARCH_TERMS
EXPORT_SEARCH_GROUPS = (
    ("general catalog pages", ("",)),
    ("English alphabet searches", ENGLISH_EXPORT_SEARCH_TERMS),
    ("Arabic alphabet searches", ARABIC_EXPORT_SEARCH_TERMS),
)

# From tawreed_product_export_retry.py
EXPORT_API_RETRY_ATTEMPTS = 3
EXPORT_API_TIMEOUT_MS = 60_000
_RETRY_DELAYS_SECONDS = (1.0, 2.0)

# From tawreed_product_export_files.py
SUPPORTED_EXPORT_FORMATS = ("csv", "xlsx", "txt")

# From tawreed_product_export_rows.py
EXPORT_FIELDNAMES = (
    "product_name_ar",
    "product_name_en",
    "store_product_id",
    "product_id",
    "available_quantity",
    "sale_price",
    "discount_percent",
    "currency",
    "store_name",
    "supplier_name",
)

# ============================================================================
# Retry Helpers (Foundation)
# ============================================================================


def post_product_export_json(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """POST one product export API request with bounded retries."""
    last_error: Exception | None = None
    for attempt in range(EXPORT_API_RETRY_ATTEMPTS):
        try:
            return _post_once(request_context, url, body, headers)
        except Exception as error:
            last_error = error
            if attempt == EXPORT_API_RETRY_ATTEMPTS - 1:
                break
            time.sleep(_RETRY_DELAYS_SECONDS[attempt])
    raise RuntimeError(f"Tawreed products export API request failed: {last_error}")


def _post_once(
    request_context: Any,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = request_context.post(
        url,
        data=body,
        headers=headers,
        timeout=EXPORT_API_TIMEOUT_MS,
    )
    if not response.ok:
        raise RuntimeError(
            f"Tawreed products export API returned HTTP {response.status}"
        )
    return response.json()

# ============================================================================
# API Helpers
# ============================================================================


def iter_all_product_candidates(
    page: Page,
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
    headers: dict[str, str] | None = None,
    request_body: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield Tawreed product candidates from every products API page."""
    emitted = 0
    for payload in _iter_product_page_payloads(
        page, page_size, headers or {}, request_body
    ):
        candidates = _api_candidates(payload)
        if not candidates:
            break
        for candidate in candidates:
            yield candidate
            emitted += 1
            if limit and emitted >= limit:
                return


def _iter_product_page_payloads(
    page: Page,
    page_size: int,
    headers: dict[str, str],
    request_body: dict[str, Any] | None,
) -> Iterator[dict[str, Any]]:
    total_pages, page_number = None, 0
    while total_pages is None or page_number < total_pages:
        payload = _fetch_products_page(
            page, page_number, page_size, headers, request_body
        )
        total_pages = _total_pages_from_payload(payload)
        yield payload
        page_number += 1


def product_export_url(page: Page, page_number: int, page_size: int) -> str:
    """Return the absolute Tawreed product-search API URL for one page."""
    origin = _api_origin(page)
    return (
        f"{origin}/rest/v2/{PRODUCT_SEARCH_ENDPOINT}"
        f"?sort=productName,asc&page={page_number}&size={page_size}"
    )


def _total_pages_from_payload(payload: dict[str, Any]) -> int:
    total_pages = int(_payload_page_data(payload).get("totalPages") or 1)
    return max(total_pages, 1)


def _fetch_products_page(
    page: Page,
    page_number: int,
    page_size: int,
    headers: dict[str, str],
    request_body: dict[str, Any] | None,
) -> dict[str, Any]:
    return post_product_export_json(
        page.request,
        product_export_url(page, page_number, page_size),
        request_body or EXPORT_REQUEST_BODY,
        headers,
    )


def _payload_page_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _api_origin(page: Page) -> str:
    origin = page.evaluate("() => location.origin")
    if "seller.tawreed.io" in str(origin):
        return "https://api.tawreed.io"
    return str(origin).rstrip("/")

# ============================================================================
# Search Helpers
# ============================================================================


@dataclass(frozen=True)
class ProductSearchRequest:
    """Reusable Tawreed product-search request metadata for one query."""

    term: str
    headers: dict[str, str]
    body: dict[str, Any]


def iter_product_search_candidates(
    page: Page,
    search_requests: Iterator[ProductSearchRequest],
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
) -> Iterator[dict[str, Any]]:
    """Yield product candidates for captured search requests in input order."""
    emitted = 0
    for search_request in search_requests:
        candidates = iter_all_product_candidates(
            page, page_size, 0, search_request.headers, search_request.body
        )
        for candidate in candidates:
            yield candidate
            emitted += 1
            if limit and emitted >= limit:
                return

# ============================================================================
# Header Helpers
# ============================================================================


def capture_product_search_headers(page: Page) -> dict[str, str]:
    """Return reusable Tawreed product-search headers from a browser request."""
    try:
        with page.expect_response(_search_response_pattern(), timeout=5000) as response:
            _submit_blank_search(page)
        return _reusable_headers(response.value.request.headers)
    except Exception:
        return {}


def capture_product_search_request(page: Page, term: str) -> ProductSearchRequest:
    """Return reusable Tawreed product-search metadata for one search term."""
    try:
        with page.expect_response(
            lambda response: _is_expected_search_response(response, term),
            timeout=5000,
        ) as response:
            _submit_search(page, term)
        request = response.value.request
        return ProductSearchRequest(
            term=term,
            headers=_reusable_headers(request.headers),
            body=_request_body(request),
        )
    except Exception as error:
        raise RuntimeError(_capture_error_message(term)) from error


def _submit_blank_search(page: Page) -> None:
    _submit_search(page, "")


def _submit_search(page: Page, term: str) -> None:
    search = page.locator(PRODUCT_SEARCH_INPUT_SELECTOR).first
    search.click()
    search.fill("")
    if term:
        search.fill(term)
    search.press("Enter")


def _request_body(request: Any) -> dict[str, Any]:
    try:
        body = request.post_data_json
    except Exception:
        body = json.loads(request.post_data or "{}")
    if isinstance(body, dict):
        return body
    raise RuntimeError("Captured Tawreed product-search request body is not an object")


def _is_expected_search_response(response: Response, term: str) -> bool:
    if not _search_response_pattern().search(response.url):
        return False
    return _search_body_term(_request_body(response.request)) == term


def _search_body_term(body: dict[str, Any]) -> str:
    data = body.get("data")
    if not isinstance(data, dict):
        return ""
    return str(data.get("productName") or "").strip()


def _capture_error_message(term: str) -> str:
    label = "general export search" if not term else f"export search '{term}'"
    return f"Could not capture Tawreed product-search request for {label}"


def _reusable_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() == "authorization" or key.lower().startswith("x-")
    }

# ============================================================================
# Row Helpers
# ============================================================================


@dataclass(frozen=True)
class ProductExportRow:
    """One normalized Tawreed store-product row for catalog exports."""

    product_name_ar: str
    product_name_en: str
    store_product_id: str
    product_id: str = ""
    available_quantity: str = ""
    sale_price: str = ""
    discount_percent: str = ""
    currency: str = ""
    store_name: str = ""
    supplier_name: str = ""

    def as_dict(self) -> dict[str, str]:
        """Return this row using the stable export field names."""
        return {
            "product_name_ar": self.product_name_ar,
            "product_name_en": self.product_name_en,
            "store_product_id": self.store_product_id,
            "product_id": self.product_id,
            "available_quantity": self.available_quantity,
            "sale_price": self.sale_price,
            "discount_percent": self.discount_percent,
            "currency": self.currency,
            "store_name": self.store_name,
            "supplier_name": self.supplier_name,
        }

    def values(self) -> list[str]:
        """Return row values in the stable export field order."""
        return [self.as_dict()[field] for field in EXPORT_FIELDNAMES]


def product_export_rows(
    candidates: Iterable[dict[str, Any]],
) -> Iterator[ProductExportRow]:
    """Yield unique normalized rows from Tawreed API product candidates."""
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        row = _row_from_candidate(candidate)
        identity = _row_identity(row)
        if identity == ("", "", "") or identity in seen:
            continue
        seen.add(identity)
        yield row


def _row_identity(row: ProductExportRow) -> tuple[str, str, str]:
    product_key = row.store_product_id or row.product_id
    return row.product_name_ar, row.product_name_en, product_key


def _row_from_candidate(candidate: dict[str, Any]) -> ProductExportRow:
    return ProductExportRow(
        product_name_ar=str(candidate.get("productName") or "").strip(),
        product_name_en=str(candidate.get("productNameEn") or "").strip(),
        store_product_id=str(candidate.get("storeProductId") or "").strip(),
        product_id=str(candidate.get("productId") or "").strip(),
        available_quantity=str(candidate.get("availableQuantity")
                                or "").strip(),
        sale_price=_field_value(candidate, "retailPrice", "salePrice"),
        discount_percent=str(candidate.get("discountPercent")
                              or "").strip(),
        currency=str(candidate.get("currency") or "").strip(),
        store_name=str(candidate.get("storeName") or "").strip(),
        supplier_name=str(candidate.get("supplierName") or "").strip(),
    )


def _field_value(candidate: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = candidate.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""

# ============================================================================
# Collection Helpers
# ============================================================================


@dataclass(frozen=True)
class ProductExportCollection:
    """Unique collected product export candidates and scan counters."""

    candidates: list[dict[str, Any]]
    scanned_count: int
    duplicates_removed: int


@dataclass
class _ScanCounter:
    scanned_count: int = 0


def collect_unique_product_candidates(
    candidates: Iterable[dict[str, Any]], limit: int = 0
) -> ProductExportCollection:
    """Return unique candidates, applying limit to final unique products."""
    counter = _ScanCounter()
    counted_candidates = _count_candidates(candidates, counter)
    unique_candidates = list(_limit_candidates(
        deduplicate_products(counted_candidates), limit
    ))
    duplicates_removed = count_duplicates_removed(
        counter.scanned_count, len(unique_candidates)
    )
    return ProductExportCollection(
        candidates=unique_candidates,
        scanned_count=counter.scanned_count,
        duplicates_removed=duplicates_removed,
    )


def product_export_collection_summary(collection: ProductExportCollection) -> str:
    """Return a concise export collection log message."""
    return (
        "Tawreed products scanned: "
        f"{collection.scanned_count}; unique exported: {len(collection.candidates)}; "
        f"duplicates removed: {collection.duplicates_removed}"
    )


def _count_candidates(
    candidates: Iterable[dict[str, Any]], counter: _ScanCounter
) -> Iterator[dict[str, Any]]:
    for candidate in candidates:
        counter.scanned_count += 1
        yield candidate


def _limit_candidates(
    candidates: Iterable[dict[str, Any]], limit: int
) -> Iterator[dict[str, Any]]:
    iterator = iter(candidates)
    emitted = 0
    while not limit or emitted < limit:
        try:
            candidate = next(iterator)
        except StopIteration:
            return
        yield candidate
        emitted += 1

# ============================================================================
# File Helpers
# ============================================================================


def write_product_export_files(
    rows: Iterable[ProductExportRow], output_dir: Path, stem: str
) -> dict[str, Path]:
    """Write Tawreed product export rows to CSV, XLSX, and tab-delimited TXT."""
    materialized_rows = list(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        "csv": _write_csv(materialized_rows, output_dir / f"{stem}.csv"),
        "xlsx": _write_xlsx(materialized_rows, output_dir / f"{stem}.xlsx"),
        "txt": _write_txt(materialized_rows, output_dir / f"{stem}.txt"),
    }


def _write_csv(rows: list[ProductExportRow], path: Path) -> Path:
    with path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(EXPORT_FIELDNAMES)
        writer.writerows(row.values() for row in rows)
    return path


def _write_xlsx(rows: list[ProductExportRow], path: Path) -> Path:
    workbook = Workbook(write_only=True)
    worksheet = workbook.create_sheet("tawreed_products")
    worksheet.append(list(EXPORT_FIELDNAMES))
    for row in rows:
        worksheet.append(row.values())
    workbook.save(path)
    return path


def _write_txt(rows: list[ProductExportRow], path: Path) -> Path:
    with path.open("w", encoding="utf-8", newline="") as output_file:
        output_file.write("\t".join(EXPORT_FIELDNAMES) + "\n")
        for row in rows:
            output_file.write("\t".join(row.values()) + "\n")
    return path

# ============================================================================
# Flow Helpers (Main Entry Point)
# ============================================================================


def export_tawreed_products(
    bot: Any,
    output_dir: Path,
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
    stem: str = DEFAULT_EXPORT_STEM,
) -> dict[str, Path]:
    """Export all visible Tawreed store products for one authenticated profile."""
    from playwright.sync_api import sync_playwright
    from .tawreed_artifacts import dump_artifacts
    from .tawreed_session import close_browser, close_context, open_order_page

    with sync_playwright() as playwright:
        browser, context, page = _open_export_page(playwright, bot)
        return _run_export_session(
            bot, page, context, browser, output_dir, page_size, limit, stem
        )


def _open_export_page(playwright, bot):
    from .tawreed_session import open_order_page

    return open_order_page(
        playwright,
        bot.config.runtime,
        bot.state_path,
        debug_browser=bot.debug_browser,
    )


def _run_export_session(
    bot, page, context, browser, output_dir, page_size, limit, stem
):
    from .tawreed_artifacts import dump_artifacts
    from .tawreed_session import close_browser, close_context

    try:
        paths = _export_from_page(bot, page, output_dir, page_size, limit, stem)
        _log_export_paths(bot, paths)
        return paths
    except Exception as error:
        _dump_export_error(bot, page, error)
        raise
    finally:
        close_context(context)
        close_browser(browser)


def _export_from_page(bot, page, output_dir, page_size, limit, stem) -> dict[str, Path]:
    bot._prepare_order_page(page)
    searches = _captured_search_requests(bot, page)
    candidates = iter_product_search_candidates(page, searches, page_size)
    collection = collect_unique_product_candidates(candidates, limit)
    bot.log(product_export_collection_summary(collection))
    rows = product_export_rows(collection.candidates)
    return write_product_export_files(rows, output_dir, stem)


def _captured_search_requests(bot, page):
    for label, terms in EXPORT_SEARCH_GROUPS:
        bot.log(f"Exporting Tawreed products: {label}")
        for term in terms:
            yield capture_product_search_request(page, term)


def _log_export_paths(bot, paths: dict[str, Path]) -> None:
    formatted_paths = ", ".join(str(path) for path in paths.values())
    bot.log(f"Tawreed products exported to: {formatted_paths}")


def _dump_export_error(bot, page, error: Exception) -> None:
    from .tawreed_artifacts import dump_artifacts

    dump_artifacts(
        page,
        bot.profile_key,
        label="product_export_error",
        details=f"product_export_error: {type(error).__name__}: {error}\n",
    )
