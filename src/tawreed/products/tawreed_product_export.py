"""Tawreed product catalog export - re-exports from split modules."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page

# Re-export from split modules
from .product_export_api import (
    DEFAULT_EXPORT_PAGE_SIZE,
    EXPORT_REQUEST_BODY,
    EXPORT_API_RETRY_ATTEMPTS,
    EXPORT_API_TIMEOUT_MS,
    post_product_export_json,
    iter_all_product_candidates,
    product_export_url,
)
from .product_export_searches import (
    ENGLISH_EXPORT_SEARCH_TERMS,
    ARABIC_EXPORT_SEARCH_TERMS,
    EXPORT_SEARCH_TERMS,
    EXPORT_SEARCH_GROUPS,
    ProductSearchRequest,
    iter_product_search_candidates,
)
from .product_export_headers import (
    capture_product_search_headers,
    capture_product_search_request,
)
from .product_export_rows import (
    EXPORT_FIELDNAMES,
    ProductExportRow,
    product_export_rows,
)
from .product_export_collection import (
    ProductExportCollection,
    collect_unique_product_candidates,
    product_export_collection_summary,
)
from .product_export_files import (
    SUPPORTED_EXPORT_FORMATS,
    DEFAULT_EXPORT_STEM,
    write_product_export_files,
)

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


__all__ = [
    # Re-exports
    "DEFAULT_EXPORT_PAGE_SIZE",
    "DEFAULT_EXPORT_STEM",
    "EXPORT_REQUEST_BODY",
    "EXPORT_API_RETRY_ATTEMPTS",
    "EXPORT_API_TIMEOUT_MS",
    "ENGLISH_EXPORT_SEARCH_TERMS",
    "ARABIC_EXPORT_SEARCH_TERMS",
    "EXPORT_SEARCH_TERMS",
    "EXPORT_SEARCH_GROUPS",
    "SUPPORTED_EXPORT_FORMATS",
    "EXPORT_FIELDNAMES",
    "ProductSearchRequest",
    "ProductExportRow",
    "ProductExportCollection",
    "post_product_export_json",
    "iter_all_product_candidates",
    "product_export_url",
    "iter_product_search_candidates",
    "capture_product_search_headers",
    "capture_product_search_request",
    "product_export_rows",
    "collect_unique_product_candidates",
    "product_export_collection_summary",
    "write_product_export_files",
    # Main entry point
    "export_tawreed_products",
]
