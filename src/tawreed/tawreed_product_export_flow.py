"""Browser-backed Tawreed product catalog export flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from .tawreed_artifacts import dump_artifacts
from .tawreed_product_export_api import (
    DEFAULT_EXPORT_PAGE_SIZE,
    DEFAULT_EXPORT_STEM,
)
from .tawreed_product_export_collection import (
    collect_unique_product_candidates,
    product_export_collection_summary,
)
from .tawreed_product_export_files import write_product_export_files
from .tawreed_product_export_headers import capture_product_search_request
from .tawreed_product_export_rows import product_export_rows
from .tawreed_product_export_searches import (
    EXPORT_SEARCH_GROUPS,
    iter_product_search_candidates,
)
from .tawreed_session import close_browser, close_context, open_order_page


def export_tawreed_products(
    bot: Any,
    output_dir: Path,
    page_size: int = DEFAULT_EXPORT_PAGE_SIZE,
    limit: int = 0,
    stem: str = DEFAULT_EXPORT_STEM,
) -> dict[str, Path]:
    """Export all visible Tawreed store products for one authenticated profile."""
    with sync_playwright() as playwright:
        browser, context, page = _open_export_page(playwright, bot)
        return _run_export_session(
            bot, page, context, browser, output_dir, page_size, limit, stem
        )


def _open_export_page(playwright, bot):
    return open_order_page(
        playwright,
        bot.config.runtime,
        bot.state_path,
        debug_browser=bot.debug_browser,
    )


def _run_export_session(
    bot, page, context, browser, output_dir, page_size, limit, stem
):
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
    dump_artifacts(
        page,
        bot.profile_key,
        label="product_export_error",
        details=f"product_export_error: {type(error).__name__}: {error}\n",
    )
