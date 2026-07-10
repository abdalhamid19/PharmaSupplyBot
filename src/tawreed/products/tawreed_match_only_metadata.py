"""Browser match-only store metadata helpers."""

from __future__ import annotations

from src.core.matching_types import SearchMatch


def record_match_only_store_metadata(
    bot, page, match: SearchMatch, active_query: str | None
) -> None:
    """Record the store that match-only would choose without touching the cart."""
    from ..store.tawreed_store_summary import record_single_store

    record_single_store(bot, match.data)
    if int(match.data.get("productsCount") or 0) <= 0:
        return
    try:
        choice = match_only_store_choice(bot, page, match, active_query)
    except Exception:
        return
    if choice:
        record_single_store(bot, choice.store)


def match_only_store_choice(bot, page, match: SearchMatch, active_query: str | None):
    """Return the browser store choice for match-only metadata."""
    stores = match_only_store_rows(bot, page, match, active_query)
    return choose_match_only_store(bot, stores)


def match_only_store_rows(bot, page, match: SearchMatch, active_query: str | None):
    """Return store rows from the product details dialog."""
    from .tawreed_products_flow import (
        matched_product_row,
        open_stores_dialog,
    )

    row = matched_product_row(bot, page, match, active_query)
    return open_stores_dialog(bot, page, row)


def choose_match_only_store(bot, stores):
    """Choose the match-only store using the configured strategy."""
    from .tawreed_products_flow import _min_disc, _preferred_warehouses, _wh_mode
    from ..store.tawreed_store_selection import choose_next_store_for_remaining_quantity

    return choose_next_store_for_remaining_quantity(
        stores,
        None,
        _wh_mode(bot),
        bot.skip_item_exception,
        _min_disc(bot),
        _preferred_warehouses(bot),
    )


__all__ = [
    "choose_match_only_store",
    "match_only_store_choice",
    "match_only_store_rows",
    "record_match_only_store_metadata",
]
